package com.mulenet.api.platform;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nimbusds.jose.*;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.*;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jwt.*;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;
import org.springframework.mock.env.MockEnvironment;
import org.springframework.mock.web.*;
import org.springframework.security.oauth2.jwt.*;
import static org.junit.jupiter.api.Assertions.*;

class SecurityBoundaryTest {
    @Test void realOidcSignatureAudienceIssuerClockTenantAndRoles() throws Exception {
        RSAKey key = new RSAKeyGenerator(2048).keyID("fixture").generate();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        String issuer = "http://127.0.0.1:" + server.getAddress().getPort() + "/issuer";
        ObjectMapper json = new ObjectMapper();
        server.createContext("/", exchange -> {
            byte[] bytes = json.writeValueAsBytes(exchange.getRequestURI().getPath().endsWith("jwks") ? new JWKSet(key.toPublicJWK()).toJSONObject() :
                Map.of("issuer", issuer, "authorization_endpoint", issuer + "/authorize", "token_endpoint", issuer + "/token", "jwks_uri", issuer + "/jwks", "response_types_supported", List.of("code"), "subject_types_supported", List.of("public"), "id_token_signing_alg_values_supported", List.of("RS256")));
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        server.start();
        try {
            assertThrows(IllegalArgumentException.class, () -> new PlatformSecurity().oidc(issuer, "mulenet-api", "", false));
            assertThrows(IllegalArgumentException.class, () -> new PlatformSecurity().oidc("http://untrusted.example/issuer", "mulenet-api", "", true));
            JwtDecoder decoder = new PlatformSecurity().oidc(issuer, "mulenet-api", "", true);
            String good = signed(key, issuer, "mulenet-api", Instant.now().plusSeconds(60), "tenant-a");
            var principal = PlatformSecurity.principal(decoder.decode(good));
            assertEquals("actor-opaque", principal.getName());
            assertTrue(principal.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_ANALYST")));
            assertThrows(JwtException.class, () -> decoder.decode(signed(key, issuer, "other", Instant.now().plusSeconds(60), "tenant-a")));
            assertThrows(JwtException.class, () -> decoder.decode(signed(key, issuer + "-wrong", "mulenet-api", Instant.now().plusSeconds(60), "tenant-a")));
            assertThrows(JwtException.class, () -> decoder.decode(signed(key, issuer, "mulenet-api", Instant.now().minusSeconds(600), "tenant-a")));
            assertThrows(JwtException.class, () -> decoder.decode(signed(key, issuer, "mulenet-api", Instant.now().plusSeconds(60), null)));
            RSAKey other = new RSAKeyGenerator(2048).keyID("unknown").generate();
            assertThrows(JwtException.class, () -> decoder.decode(signed(other, issuer, "mulenet-api", Instant.now().plusSeconds(60), "tenant-a")));
        } finally { server.stop(0); }
    }

    private static String signed(RSAKey key, String issuer, String audience, Instant expiration, String tenant) throws Exception {
        var claims = new JWTClaimsSet.Builder().issuer(issuer).subject("actor-opaque").audience(audience)
            .issueTime(new Date()).expirationTime(Date.from(expiration)).claim("realm_access", Map.of("roles", List.of("analyst")));
        if (tenant != null) claims.claim("tenant", tenant);
        SignedJWT token = new SignedJWT(new JWSHeader.Builder(JWSAlgorithm.RS256).keyID(key.getKeyID()).build(), claims.build());
        token.sign(new RSASSASigner(key));
        return token.serialize();
    }

    @Test void purposeSeparatedSignaturesRejectLateralForgery() {
        String ml = UUID.randomUUID().toString() + UUID.randomUUID();
        String stream = UUID.randomUUID().toString() + UUID.randomUUID();
        String ingestion = UUID.randomUUID().toString() + UUID.randomUUID();
        ServiceTokens tokens = new ServiceTokens(ml, stream, ingestion);
        var decoder = new PlatformSecurity().streamDecoder(stream);
        String validStream = tokens.stream("tenant-a", "actor", List.of("ANALYST"), Instant.now().plusSeconds(30));
        assertEquals("tenant-a", decoder.decode(validStream).getClaimAsString("tenant"));
        assertThrows(JwtException.class, () -> decoder.decode(tokens.ml("tenant-a")));
        assertThrows(io.jsonwebtoken.JwtException.class, () -> tokens.verifyIngestion(validStream));
        assertThrows(JwtException.class, () -> decoder.decode(tokens.stream("tenant-a", "actor", List.of("ADMIN"), Instant.now().plusSeconds(120))));
        assertThrows(IllegalArgumentException.class, () -> new ServiceTokens(ml, ml, ml));
    }

    @Test void boundsQueriesAndLoginRateAreEnforcedBeforeParsing() throws Exception {
        RequestGuards guard = new RequestGuards();
        MockHttpServletRequest oversized = new MockHttpServletRequest("POST", "/api/v1/transactions");
        oversized.setContentType("application/json"); oversized.setContent(new byte[2_000_001]);
        MockHttpServletResponse rejected = new MockHttpServletResponse();
        guard.doFilter(oversized, rejected, (request, response) -> fail("Oversized body passed guard"));
        assertEquals(413, rejected.getStatus());
        MockHttpServletRequest query = new MockHttpServletRequest("GET", "/api/v1/events"); query.addParameter("token", "not-a-bearer-header");
        MockHttpServletResponse queryRejected = new MockHttpServletResponse();
        guard.doFilter(query, queryRejected, (request, response) -> fail("Query credential passed guard"));
        assertEquals(401, queryRejected.getStatus());
        for (int attempt = 0; attempt < 6; attempt++) {
            var request = new MockHttpServletRequest("POST", "/api/v1/auth/login");
            request.setRemoteAddr("198.18.0.1"); request.addHeader("X-Forwarded-For", "198.18.0." + attempt);
            var response = new MockHttpServletResponse();
            guard.doFilter(request, response, (r, s) -> {});
            assertEquals(attempt < 5 ? 200 : 429, response.getStatus());
        }
    }

    @Test void scalarCoercionAndLegacyProfilesFailClosed() throws Exception {
        var builder = new Jackson2ObjectMapperBuilder();
        new StrictJson().strictScalarTypes().customize(builder);
        ObjectMapper json = builder.build();
        assertThrows(Exception.class, () -> json.readValue("{\"maxHoldSeconds\":\"900\",\"reviewThreshold\":0.5,\"falseFreezeCostInr\":1000,\"missedRiskCostInr\":10000}", ReviewPolicy.class));
        assertThrows(Exception.class, () -> json.readValue("{\"fraudulent\":\"false\",\"evidence\":\"independent source confirmed\"}", PlatformController.Feedback.class));
        MockEnvironment legacy = new MockEnvironment(); legacy.setActiveProfiles("legacy");
        assertThrows(IllegalArgumentException.class, () -> new ConfigurationGuard(legacy));
        MockEnvironment correct = new MockEnvironment(); correct.setActiveProfiles("platform", "demo");
        assertDoesNotThrow(() -> new ConfigurationGuard(correct));
    }
}
