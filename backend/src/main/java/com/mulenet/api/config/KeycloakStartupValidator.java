package com.mulenet.api.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import jakarta.annotation.PostConstruct;
import java.net.URI;

@Component
@ConditionalOnProperty(name = "app.security.oauth2.enabled", havingValue = "true")
public class KeycloakStartupValidator {

    private static final Logger logger = LoggerFactory.getLogger(KeycloakStartupValidator.class);

    @Value("${spring.security.oauth2.resourceserver.jwt.issuer-uri}")
    private String issuerUri;

    @PostConstruct
    public void validateKeycloak() {
        logger.info("OAuth2 is enabled. Validating Keycloak issuer URI: {}", issuerUri);
        RestTemplate restTemplate = new RestTemplate();
        try {
            String wellKnownUrl = issuerUri + "/.well-known/openid-configuration";
            restTemplate.getForEntity(new URI(wellKnownUrl), String.class);
            logger.info("Successfully connected to Keycloak.");
        } catch (Exception e) {
            logger.error("Failed to connect to Keycloak at {}. " +
                    "Failing fast as OAUTH2_ENABLED=true.", issuerUri, e);
            throw new RuntimeException("Keycloak unreachable at startup. Aborting.", e);
        }
    }
}
