package com.mulenet.api.model;

import jakarta.persistence.*;

@Entity
@Table(name = "external_watchlist")
public class ExternalWatchlist {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String accountId;

    @Column(nullable = false)
    private String source;

    private double riskUplift;

    private String matchType;

    private double confidence;

    private String details;

    public ExternalWatchlist() {}

    public ExternalWatchlist(String accountId, String source, double riskUplift, String matchType, double confidence, String details) {
        this.accountId = accountId;
        this.source = source;
        this.riskUplift = riskUplift;
        this.matchType = matchType;
        this.confidence = confidence;
        this.details = details;
    }

    // Getters and Setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getAccountId() {
        return accountId;
    }

    public void setAccountId(String accountId) {
        this.accountId = accountId;
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
}
