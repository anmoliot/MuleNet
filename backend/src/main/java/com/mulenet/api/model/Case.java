package com.mulenet.api.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "cases")
public class Case {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false)
    private String caseId;

    private String complaintId;

    @Enumerated(EnumType.STRING)
    private CaseStatus status = CaseStatus.OPEN;

    private Double riskScore;

    private String assignedTo;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    private LocalDateTime resolvedAt;

    @Column(columnDefinition = "CLOB")
    private String mlResponse;

    @Column(columnDefinition = "CLOB")
    private String policyDecisions;

    private Integer accountsAnalyzed;

    private Integer accountsFlagged;

    private String severityLevel;

    public Case() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    public enum CaseStatus {
        OPEN, INVESTIGATING, ESCALATED, FROZEN, CLOSED, DISMISSED
    }

    // Getters and Setters

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getCaseId() { return caseId; }
    public void setCaseId(String caseId) { this.caseId = caseId; }

    public String getComplaintId() { return complaintId; }
    public void setComplaintId(String complaintId) { this.complaintId = complaintId; }

    public CaseStatus getStatus() { return status; }
    public void setStatus(CaseStatus status) {
        this.status = status;
        this.updatedAt = LocalDateTime.now();
    }

    public Double getRiskScore() { return riskScore; }
    public void setRiskScore(Double riskScore) { this.riskScore = riskScore; }

    public String getAssignedTo() { return assignedTo; }
    public void setAssignedTo(String assignedTo) { this.assignedTo = assignedTo; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }

    public LocalDateTime getResolvedAt() { return resolvedAt; }
    public void setResolvedAt(LocalDateTime resolvedAt) { this.resolvedAt = resolvedAt; }

    public String getMlResponse() { return mlResponse; }
    public void setMlResponse(String mlResponse) { this.mlResponse = mlResponse; }

    public String getPolicyDecisions() { return policyDecisions; }
    public void setPolicyDecisions(String policyDecisions) { this.policyDecisions = policyDecisions; }

    public Integer getAccountsAnalyzed() { return accountsAnalyzed; }
    public void setAccountsAnalyzed(Integer accountsAnalyzed) { this.accountsAnalyzed = accountsAnalyzed; }

    public Integer getAccountsFlagged() { return accountsFlagged; }
    public void setAccountsFlagged(Integer accountsFlagged) { this.accountsFlagged = accountsFlagged; }

    public String getSeverityLevel() { return severityLevel; }
    public void setSeverityLevel(String severityLevel) { this.severityLevel = severityLevel; }
}
