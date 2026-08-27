package com.mulenet.api.controller;

import com.mulenet.api.dto.PredictionRequest;
import com.mulenet.api.model.Prediction;
import com.mulenet.api.repository.PredictionRepository;
import com.mulenet.api.service.MlService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/prediction")
public class PredictionController {

    private static final Logger logger = LoggerFactory.getLogger(PredictionController.class);

    @Autowired
    private MlService mlService;

    @Autowired
    private PredictionRepository predictionRepository;

    @PostMapping
    @PreAuthorize("hasAnyRole('ANALYST','FRAUD_ADMIN')")
    public ResponseEntity<Prediction> predict(@RequestBody PredictionRequest request) {
        logger.info("Received prediction request for account {}", request.getAccountId());
        // Call ML service to get analysis JSON
        String mlResponse = mlService.analyzeGraph(request.getIntakeRequest());
        // For simplicity, store raw response in Prediction entity (parsing omitted)
        Prediction prediction = new Prediction();
        prediction.setAccountId(request.getAccountId());
        prediction.setModelVersion("v1"); // placeholder version
        prediction.setRiskScore(0.0); // placeholder, should be parsed from mlResponse
        prediction.setRiskLevel("UNKNOWN");
        prediction.setFraudProbability(0.0);
        prediction.setConfidence(1.0);
        prediction.setFastPathScore(null);
        prediction.setGnnScore(null);
        prediction.setTopologyScore(null);
        prediction.setAnomalyScore(null);
        prediction.setExternalUplift(null);
        prediction.setShapExplanation(null);
        prediction.setLimeExplanation(null);
        prediction.setActionRecommended(null);
        // Store raw ML response in a JSONB column (optional) – omitted for brevity
        predictionRepository.save(prediction);
        logger.info("Stored prediction with id {}", prediction.getId());
        return ResponseEntity.ok(prediction);
    }
}
