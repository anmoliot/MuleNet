package com.mulenet.api.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.beans.factory.annotation.Value;

@Service
public class MlService {

    private static final Logger logger = LoggerFactory.getLogger(MlService.class);

    private final RestTemplate restTemplate;

    @Value("${app.ml-service.url:http://localhost:8000/api/analyze}")
    private String mlServiceUrl;

    public MlService() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(30000);  // ML inference can take time
        this.restTemplate = new RestTemplate(factory);
    }

    public String analyzeGraph(com.mulenet.api.dto.IntakeRequest payload) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<com.mulenet.api.dto.IntakeRequest> request = new HttpEntity<>(payload, headers);

        long start = System.currentTimeMillis();
        logger.info("Sending graph analysis request payload to ML service at: {}", mlServiceUrl);
        try {
            ResponseEntity<String> response = restTemplate.postForEntity(mlServiceUrl, request, String.class);
            long latency = System.currentTimeMillis() - start;
            logger.info("Successfully received analysis response from ML service in {}ms", latency);
            return response.getBody();
        } catch (Exception e) {
            long latency = System.currentTimeMillis() - start;
            logger.error("Failed to connect or receive response from ML service at {} (attempt took {}ms): {}", 
                    mlServiceUrl, latency, e.getMessage(), e);
            String msg = e.getMessage() != null ? e.getMessage().replace("\"", "\\\"").replace("\n", " ").replace("\r", "") : "Unknown error";
            return "{\"error\": \"Failed to connect to ML service: " + msg + "\", \"status\": \"error\"}";
        }
    }
}
