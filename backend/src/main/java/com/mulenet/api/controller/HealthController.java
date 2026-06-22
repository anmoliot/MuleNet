package com.mulenet.api.controller;

import com.mulenet.api.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@RestController
public class HealthController {

    private static final Logger logger = LoggerFactory.getLogger(HealthController.class);

    @Autowired
    private UserRepository userRepository;

    @Value("${app.ml-service.url:http://localhost:8000/api/analyze}")
    private String mlServiceUrl;

    @GetMapping("/api/health")
    public ResponseEntity<Map<String, Object>> health() {
        logger.info("Executing detailed health check status...");
        Map<String, Object> status = new HashMap<>();
        boolean dbUp = false;
        boolean mlUp = false;

        // 1. Check Database Connectivity
        try {
            userRepository.count();
            dbUp = true;
            status.put("database", "UP");
        } catch (Exception e) {
            logger.error("Health check failed for database connectivity: {}", e.getMessage(), e);
            status.put("database", "DOWN: " + e.getMessage());
        }

        // 2. Check ML Service reachability
        try {
            String mlHealthUrl = mlServiceUrl.replace("/api/analyze", "/api/health");
            RestTemplate restTemplate = new RestTemplate();
            Map<?, ?> response = restTemplate.getForObject(mlHealthUrl, Map.class);
            if (response != null && "ok".equals(response.get("status"))) {
                mlUp = true;
                status.put("mlService", "UP");
                status.put("mlServiceDetails", response);
            } else {
                status.put("mlService", "DOWN: Invalid response status");
            }
        } catch (Exception e) {
            logger.error("Health check failed for ML service connectivity: {}", e.getMessage());
            status.put("mlService", "DOWN: " + e.getMessage());
        }

        if (dbUp && mlUp) {
            status.put("status", "UP");
            return ResponseEntity.ok(status);
        } else {
            status.put("status", "DOWN");
            return ResponseEntity.status(503).body(status);
        }
    }

    @GetMapping("/api/readiness")
    public ResponseEntity<Map<String, Object>> readiness() {
        logger.info("Executing readiness check status...");
        Map<String, Object> status = new HashMap<>();
        try {
            userRepository.count();
            status.put("status", "UP");
            status.put("database", "CONNECTED");
            return ResponseEntity.ok(status);
        } catch (Exception e) {
            logger.error("Readiness check failed for database: {}", e.getMessage());
            status.put("status", "DOWN");
            status.put("database", "DISCONNECTED: " + e.getMessage());
            return ResponseEntity.status(503).body(status);
        }
    }
}
