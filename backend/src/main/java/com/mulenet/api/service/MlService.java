package com.mulenet.api.service;

import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;

@Service
public class MlService {

    private final RestTemplate restTemplate;
    private final String ML_SERVICE_URL = "http://localhost:8000/api/analyze";

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

        try {
            ResponseEntity<String> response = restTemplate.postForEntity(ML_SERVICE_URL, request, String.class);
            return response.getBody();
        } catch (Exception e) {
            e.printStackTrace();
            String msg = e.getMessage() != null ? e.getMessage().replace("\"", "\\\"").replace("\n", " ").replace("\r", "") : "Unknown error";
            return "{\"error\": \"Failed to connect to ML service: " + msg + "\", \"status\": \"error\"}";
        }
    }
}
