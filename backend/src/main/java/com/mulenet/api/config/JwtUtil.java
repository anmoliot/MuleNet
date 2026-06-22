package com.mulenet.api.config;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import jakarta.annotation.PostConstruct;

import java.security.Key;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

@Component
public class JwtUtil {

    @Value("${app.security.jwt.secret:dGhpcy1pcy1hLXNlY3VyZS0yNTYtYml0LXNpZ25pbmcta2V5LWZvci1tdWxlbmV0LWFwaS1wbGF0Zm9ybQ==}")
    private String jwtSecret;

    @Value("${spring.profiles.active:}")
    private String activeProfiles;

    private Key key;

    private static final String DEFAULT_SECRET = "dGhpcy1pcy1hLXNlY3VyZS0yNTYtYml0LXNpZ25pbmcta2V5LWZvci1tdWxlbmV0LWFwaS1wbGF0Zm9ybQ==";

    // 10 hours expiration
    private static final long EXPIRATION_TIME = 1000 * 60 * 60 * 10;

    @PostConstruct
    public void init() {
        if (activeProfiles != null && activeProfiles.contains("prod")) {
            if (jwtSecret == null || jwtSecret.trim().isEmpty() || jwtSecret.equals(DEFAULT_SECRET)) {
                throw new IllegalStateException("FATAL: Insecure JWT Secret detected in production! " +
                        "A unique and secure JWT secret must be supplied via the 'JWT_SECRET' environment variable.");
            }
        }
        this.key = Keys.hmacShaKeyFor(jwtSecret.getBytes());
    }

    public String generateToken(String username, String role) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("role", role);
        return createToken(claims, username);
    }

    private String createToken(Map<String, Object> claims, String subject) {
        return Jwts.builder()
                .setClaims(claims)
                .setSubject(subject)
                .setIssuedAt(new Date(System.currentTimeMillis()))
                .setExpiration(new Date(System.currentTimeMillis() + EXPIRATION_TIME))
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();
    }

    public Boolean validateToken(String token, String username) {
        final String tokenUsername = extractUsername(token);
        return (tokenUsername.equals(username) && !isTokenExpired(token));
    }

    public String extractUsername(String token) {
        return extractClaim(token, Claims::getSubject);
    }

    public String extractRole(String token) {
        final Claims claims = extractAllClaims(token);
        return claims.get("role", String.class);
    }

    public Date extractExpiration(String token) {
        return extractClaim(token, Claims::getExpiration);
    }

    public <T> T extractClaim(String token, Function<Claims, T> claimsResolver) {
        final Claims claims = extractAllClaims(token);
        return claimsResolver.apply(claims);
    }

    private Claims extractAllClaims(String token) {
        return Jwts.parserBuilder().setSigningKey(key).build().parseClaimsJws(token).getBody();
    }

    private Boolean isTokenExpired(String token) {
        return extractExpiration(token).before(new Date());
    }
}
