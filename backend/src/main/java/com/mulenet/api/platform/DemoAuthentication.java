package com.mulenet.api.platform;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@Profile("platform & demo")
public class DemoAuthentication {
    private final Map<String, String> passwords;
    private final byte[] signingKey;
    public DemoAuthentication(@Value("${mulenet.demo-passwords.analyst}") String analyst,
                              @Value("${mulenet.demo-passwords.supervisor}") String supervisor,
                              @Value("${mulenet.demo-passwords.admin}") String admin,
                              @Value("${mulenet.demo-passwords.auditor}") String auditor,
                              @Value("${mulenet.demo-jwt-secret}") String key) {
        passwords = Map.of("analyst", analyst, "supervisor", supervisor, "admin", admin, "auditor", auditor);
        if (passwords.values().stream().anyMatch(p -> p.length() < 24) || new HashSet<>(passwords.values()).size() != 4)
            throw new IllegalArgumentException("Unique per-install demo passwords required");
        signingKey = Base64.getDecoder().decode(key);
    }
    public record Login(@NotBlank @Size(max = 64) String username, @NotBlank @Size(max = 256) String password) {}
    @PostMapping("/api/v1/auth/login")
    public Map<String, Object> login(@Valid @RequestBody Login request) {
        String expected = passwords.getOrDefault(request.username(), "invalid-user-denied");
        if (!MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8), request.password().getBytes(StandardCharsets.UTF_8)) || !passwords.containsKey(request.username()))
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid credentials");
        Instant now = Instant.now();
        String token = Jwts.builder().setIssuer("mulenet-demo").setAudience("mulenet-api").setSubject("demo-" + request.username())
            .setId(UUID.randomUUID().toString()).setIssuedAt(Date.from(now)).setExpiration(Date.from(now.plusSeconds(300)))
            .claim("roles", List.of(request.username())).claim("tenant", "demo")
            .signWith(Keys.hmacShaKeyFor(signingKey), SignatureAlgorithm.HS256).compact();
        return Map.of("access_token", token, "expires_in", 300, "role", request.username(), "tenant", "demo", "simulated", true);
    }
}
