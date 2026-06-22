package com.mulenet.api.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "threat_intelligence")
public class ExternalWatchlist {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "ioc_type", nullable = false, length = 32)
    private String iocType;

    @Column(name = "ioc_value", nullable = false, length = 512)
    private String accountId;

    @Column(nullable = false, length = 128)
    private String source;

    @Column(name = "risk_weight")
    private double riskUplift;

    @Column(name = "category", nullable = false, length = 64)
    private String matchType;

    private double confidence = 1.0;

    @Column(name = "description", columnDefinition = "TEXT")
    private String details;

    @Column(name = "is_active")
    private boolean isActive = true;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    public ExternalWatchlist() {}

    public ExternalWatchlist(String accountId, String source, double riskUplift, String matchType, double confidence, String details) {
        this.accountId = accountId;
        this.source = source;
        this.riskUplift = riskUplift;
        this.matchType = matchType;
        this.confidence = confidence;
        this.details = details;
        this.iocType = (accountId != null && (accountId.startsWith("DEV-") || accountId.startsWith("device:"))) ? "device" : "account";
        this.isActive = true;
        this.createdAt = LocalDateTime.now();
    }

    // Getters and Setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getIocType() {
        return iocType;
    }

    public void setIocType(String iocType) {
        this.iocType = iocType;
    }

    public String getAccountId() {
        return accountId;
    }

    public void setAccountId(String accountId) {
        this.accountId = accountId;
        this.iocType = (accountId != null && (accountId.startsWith("DEV-") || accountId.startsWith("device:"))) ? "device" : "account";
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public double getRiskUplift() {
        return riskUplift;
    }

    public void setRiskUplift(double riskUplift) {
        this.riskUplift = riskUplift;
    }

    public String getMatchType() {
        return matchType;
    }

    public void setMatchType(String matchType) {
        this.matchType = matchType;
    }

    public double getConfidence() {
        return confidence;
    }

    public void setConfidence(double confidence) {
        this.confidence = confidence;
    }

    public String getDetails() {
        return details;
    }

    public void setDetails(String details) {
        this.details = details;
    }

    public boolean isWarningActive() {
        return isActive;
    }

    public void setWarningActive(boolean active) {
        isActive = active;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}

