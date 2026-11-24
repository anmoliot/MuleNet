package com.mulenet.api.platform;

import java.nio.charset.StandardCharsets;
import java.util.*;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.core.*;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.web.cors.*;

@Configuration
@Profile("platform")
@EnableMethodSecurity
public class PlatformSecurity {
    private static final Set<String> ROLES = Set.of("ANALYST", "SUPERVISOR", "ADMIN", "AUDITOR");

    static OAuth2TokenValidator<Jwt> audience(String value) {
        return token -> token.getAudience().contains(value) ? OAuth2TokenValidatorResult.success() :
            OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "Invalid audience", null));
    }

    static JwtAuthenticationToken principal(Jwt jwt) {
        List<String> roles = jwt.getClaimAsStringList("roles");
        if (roles == null) {
            Map<String, Object> realm = jwt.getClaimAsMap("realm_access");
            roles = realm != null && realm.get("roles") instanceof List<?> list ? list.stream().filter(String.class::isInstance).map(String.class::cast).toList() : List.of();
        }
        return new JwtAuthenticationToken(jwt, roles.stream().map(r -> r.toUpperCase(Locale.ROOT)).filter(ROLES::contains)
            .map(r -> new SimpleGrantedAuthority("ROLE_" + r)).toList(), jwt.getSubject());
    }

    @Bean("platformDecoder")
    @Profile("!demo")
    public JwtDecoder oidc(@Value("${mulenet.oidc-issuer}") String issuer, @Value("${mulenet.oidc-audience:mulenet-api}") String audience) {
        NimbusJwtDecoder decoder = JwtDecoders.fromIssuerLocation(issuer);
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(JwtValidators.createDefaultWithIssuer(issuer), audience(audience)));
        return decoder;
    }
    @Bean("platformDecoder")
    @Profile("demo")
    public JwtDecoder demo(@Value("${mulenet.demo-jwt-secret}") String secret) {
        byte[] key = Base64.getDecoder().decode(secret);
        if (key.length < 32) throw new IllegalArgumentException("Unique demo signing key required");
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withSecretKey(new SecretKeySpec(key, "HmacSHA256")).macAlgorithm(MacAlgorithm.HS256).build();
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(JwtValidators.createDefaultWithIssuer("mulenet-demo"), audience("mulenet-api")));
        return decoder;
    }
    @Bean("streamDecoder")
    public JwtDecoder streamDecoder(@Value("${mulenet.service-secret}") String secret) {
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withSecretKey(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256")).macAlgorithm(MacAlgorithm.HS256).build();
        OAuth2TokenValidator<Jwt> scope = token -> "sse".equals(token.getClaimAsString("scope")) && token.getExpiresAt() != null && token.getIssuedAt() != null &&
                token.getExpiresAt().getEpochSecond() - token.getIssuedAt().getEpochSecond() <= 60 ? OAuth2TokenValidatorResult.success() :
            OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "Invalid stream scope or lifetime", null));
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(JwtValidators.createDefaultWithIssuer("mulenet-backend"), audience("mulenet-sse"), scope));
        return decoder;
    }

    private void base(HttpSecurity http, String origins) throws Exception {
        CorsConfiguration cors = new CorsConfiguration();
        List<String> allowed = Arrays.stream(origins.split(",")).map(String::trim).toList();
        if (allowed.stream().anyMatch(o -> o.contains("*") || !o.matches("https?://[^/]+"))) throw new IllegalArgumentException("Exact CORS origins required");
        cors.setAllowedOrigins(allowed);
        cors.setAllowedMethods(List.of("GET", "POST", "PUT", "OPTIONS"));
        cors.setAllowedHeaders(List.of("Authorization", "Content-Type", "Last-Event-ID"));
        cors.setAllowCredentials(false);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", cors);
        http.cors(c -> c.configurationSource(source))
            // Bearer credentials are explicit headers; no session or authentication cookies.
            .csrf(csrf -> csrf.disable()).httpBasic(b -> b.disable()).formLogin(f -> f.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(e -> e.authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)))
            .headers(h -> h.contentSecurityPolicy(c -> c.policyDirectives("default-src 'none'; frame-ancestors 'none'"))
                .frameOptions(f -> f.deny()).referrerPolicy(r -> r.policy(org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter.ReferrerPolicy.NO_REFERRER)));
    }

    @Bean @Order(1)
    public SecurityFilterChain streamChain(HttpSecurity http, @Qualifier("streamDecoder") JwtDecoder decoder,
                                           @Value("${mulenet.cors-origins:http://localhost:3000,http://localhost:5173}") String origins) throws Exception {
        base(http, origins);
        return http.securityMatcher("/api/v1/events").authorizeHttpRequests(a -> a.anyRequest().hasAnyRole("ANALYST", "SUPERVISOR", "ADMIN", "AUDITOR"))
            .oauth2ResourceServer(o -> o.jwt(j -> j.decoder(decoder).jwtAuthenticationConverter(PlatformSecurity::principal))).build();
    }
    @Bean @Order(2)
    public SecurityFilterChain platformChain(HttpSecurity http, @Qualifier("platformDecoder") JwtDecoder decoder,
                                             @Value("${mulenet.cors-origins:http://localhost:3000,http://localhost:5173}") String origins) throws Exception {
        base(http, origins);
        return http.authorizeHttpRequests(a -> a
                .dispatcherTypeMatchers(jakarta.servlet.DispatcherType.ASYNC).permitAll()
                .requestMatchers("/api/health", "/api/v1/auth/login").permitAll()
                .requestMatchers("/actuator/prometheus").hasAnyRole("ADMIN", "AUDITOR")
                .requestMatchers("/api/v1/**", "/api/demo/seed").authenticated()
                .anyRequest().denyAll())
            .oauth2ResourceServer(o -> o.jwt(j -> j.decoder(decoder).jwtAuthenticationConverter(PlatformSecurity::principal))).build();
    }
}
