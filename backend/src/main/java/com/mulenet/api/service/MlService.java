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
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.retry.annotation.Recover;

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

    @Retryable(
      value = {Exception.class},
      maxAttempts = 3,
      backoff = @Backoff(delay = 2000, multiplier = 2)
    )
    public String analyzeGraph(com.mulenet.api.dto.IntakeRequest payload) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<com.mulenet.api.dto.IntakeRequest> request = new HttpEntity<>(payload, headers);

        long start = System.currentTimeMillis();
        logger.info("Sending graph analysis request payload to ML service at: {}", mlServiceUrl);
        try {
            ResponseEntity<String> response = restTemplate.postForEntity(mlServiceUrl, request, String.class);
            long latency = System.currentTimeMillis() - start;
            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new RuntimeException("ML Service returned non-2xx status: " + response.getStatusCode());
            }
            logger.info("Successfully received analysis response from ML service in {}ms", latency);
            return response.getBody();
        } catch (Exception e) {
            long latency = System.currentTimeMillis() - start;
            logger.error("Failed to connect or receive response from ML service at {} (attempt took {}ms): {}", 
                    mlServiceUrl, latency, e.getMessage());
            throw new RuntimeException("Failed to connect to ML service: " + e.getMessage(), e);
        }
    }

    @Recover
    public String recover(Exception e, com.mulenet.api.dto.IntakeRequest payload) {
        logger.error("All retries exhausted for ML Service call. Failing fast.");
        throw new RuntimeException("ML service unavailable after retries", e);
    }
}
