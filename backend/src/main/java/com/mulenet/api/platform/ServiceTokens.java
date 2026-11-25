package com.mulenet.api.platform;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.time.Instant;
import java.util.Date;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

@Component
@Profile("platform")
public class ServiceTokens {
    private final Key key;
    public ServiceTokens(@Value("${mulenet.service-secret}") String secret) {
        if (secret.getBytes(StandardCharsets.UTF_8).length < 48) throw new IllegalArgumentException("Unique service secret required");
        key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }
    public String ml(String tenant) {
        Instant now = Instant.now();
        return Jwts.builder().setIssuer("mulenet-backend").setAudience("mulenet-ml").setSubject("backend")
            .setId(UUID.randomUUID().toString()).setIssuedAt(Date.from(now)).setExpiration(Date.from(now.plusSeconds(30)))
            .claim("tenant", tenant).claim("scope", "score cache").signWith(key, io.jsonwebtoken.SignatureAlgorithm.HS256).compact();
    }
    public String ingestion(String tenant, String eventId, String body) {
        Instant now = Instant.now();
        return Jwts.builder().setIssuer("mulenet-backend").setAudience("mulenet-ingestion").setSubject("ingestion")
            .setId(eventId).setIssuedAt(Date.from(now)).setExpiration(Date.from(now.plusSeconds(86400)))
            .claim("tenant", tenant).claim("body", body).signWith(key, io.jsonwebtoken.SignatureAlgorithm.HS256).compact();
    }
    public Claims verifyIngestion(String token) {
        var parsed = Jwts.parserBuilder().setSigningKey(key).requireIssuer("mulenet-backend")
            .requireAudience("mulenet-ingestion").requireSubject("ingestion").build().parseClaimsJws(token);
        if (!parsed.getHeader().getAlgorithm().equals("HS256")) throw new IllegalArgumentException("Unsupported ingestion signature");
        Claims claims = parsed.getBody();
        if (claims.getExpiration() == null || claims.getIssuedAt() == null ||
            claims.getExpiration().getTime() - claims.getIssuedAt().getTime() > 86400000L ||
            claims.getIssuedAt().after(new Date(System.currentTimeMillis() + 3000))) throw new IllegalArgumentException("Invalid ingestion clock");
        return claims;
    }
    public String stream(String tenant, String subject, java.util.List<String> roles, Instant expires) {
        Instant now = Instant.now();
        return Jwts.builder().setIssuer("mulenet-backend").setAudience("mulenet-sse").setSubject(subject)
            .setId(UUID.randomUUID().toString()).setIssuedAt(Date.from(now)).setExpiration(Date.from(expires))
            .claim("tenant", tenant).claim("roles", roles).claim("scope", "sse")
            .signWith(key, io.jsonwebtoken.SignatureAlgorithm.HS256).compact();
    }
}
