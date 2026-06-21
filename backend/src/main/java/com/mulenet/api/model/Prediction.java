package com.mulenet.api.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "predictions")
public class Prediction {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "account_id", nullable = false, length = 64)
    private String accountId;

    @Column(name = "case_id", length = 64)
    private String caseId;

    @Column(name = "model_version", nullable = false, length = 16)
    private String modelVersion;

    @Column(name = "risk_score", nullable = false)
    private Double riskScore;

    @Column(name = "risk_level", nullable = false, length = 16)
    private String riskLevel;

    @Column(name = "fraud_probability", nullable = false)
    private Double fraudProbability;

    @Column(nullable = false)
    private Double confidence;

    @Column(name = "fast_path_score")
    private Double fastPathScore;

    @Column(name = "gnn_score")
    private Double gnnScore;

    @Column(name = "topology_score")
    private Double topologyScore;

    @Column(name = "anomaly_score")
    private Double anomalyScore;

    @Column(name = "external_uplift")
    private Double externalUplift;

    @Column(name = "shap_explanation", columnDefinition = "jsonb")
    private String shapExplanation;

    @Column(name = "lime_explanation", columnDefinition = "jsonb")
    private String limeExplanation;

    @Column(name = "action_recommended", length = 32)
    private String actionRecommended;

    @Column(name = "predicted_at", nullable = false)
    private LocalDateTime predictedAt = LocalDateTime.now();

    public Prediction() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getAccountId() { return accountId; }
    public void setAccountId(String accountId) { this.accountId = accountId; }

    public String getCaseId() { return caseId; }
    public void setCaseId(String caseId) { this.caseId = caseId; }

    public String getModelVersion() { return modelVersion; }
    public void setModelVersion(String modelVersion) { this.modelVersion = modelVersion; }

    public Double getRiskScore() { return riskScore; }
    public void setRiskScore(Double riskScore) { this.riskScore = riskScore; }

    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }

    public Double getFraudProbability() { return fraudProbability; }
    public void setFraudProbability(Double fraudProbability) { this.fraudProbability = fraudProbability; }

    public Double getConfidence() { return confidence; }
    public void setConfidence(Double confidence) { this.confidence = confidence; }

    public Double getFastPathScore() { return fastPathScore; }
    public void setFastPathScore(Double fastPathScore) { this.fastPathScore = fastPathScore; }

    public Double getGnnScore() { return gnnScore; }
    public void setGnnScore(Double gnnScore) { this.gnnScore = gnnScore; }

    public Double getTopologyScore() { return topologyScore; }
    public void setTopologyScore(Double topologyScore) { this.topologyScore = topologyScore; }

    public Double getAnomalyScore() { return anomalyScore; }
    public void setAnomalyScore(Double anomalyScore) { this.anomalyScore = anomalyScore; }

    public Double getExternalUplift() { return externalUplift; }
    public void setExternalUplift(Double externalUplift) { this.externalUplift = externalUplift; }

    public String getShapExplanation() { return shapExplanation; }
    public void setShapExplanation(String shapExplanation) { this.shapExplanation = shapExplanation; }

    public String getLimeExplanation() { return limeExplanation; }
    public void setLimeExplanation(String limeExplanation) { this.limeExplanation = limeExplanation; }

    public String getActionRecommended() { return actionRecommended; }
    public void setActionRecommended(String actionRecommended) { this.actionRecommended = actionRecommended; }

    public LocalDateTime getPredictedAt() { return predictedAt; }
    public void setPredictedAt(LocalDateTime predictedAt) { this.predictedAt = predictedAt; }
}
