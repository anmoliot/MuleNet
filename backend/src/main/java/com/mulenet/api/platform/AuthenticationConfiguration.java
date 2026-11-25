package com.mulenet.api.platform;

import java.util.Map;
import org.springframework.context.annotation.Profile;
import org.springframework.core.env.Environment;
import org.springframework.web.bind.annotation.*;

@RestController
@Profile("platform")
public class AuthenticationConfiguration {
    private final Environment environment;
    public AuthenticationConfiguration(Environment environment) { this.environment = environment; }
    @GetMapping("/api/v1/auth/config")
    public Map<String, Object> configuration() {
        if (environment.matchesProfiles("demo")) return Map.of("mode", "demo", "simulated", true, "production_approved", false);
        return Map.of("mode", "oidc", "issuer", environment.getRequiredProperty("mulenet.oidc-issuer"), "client_id", "mulenet-ui", "production_approved", false);
    }
}
