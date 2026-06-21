package com.mulenet.api.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "cases")
public class Case {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "case_id", unique = true, nullable = false, length = 64)
    private String caseId;

    @Column(name = "complaint_id", length = 64)
    private String complaintId;

    @Enumerated(EnumType.STRING)
    @Column(length = 32)
    private CaseStatus status = CaseStatus.OPEN;

    @Column(name = "risk_score")
    private Double riskScore;

    @Column(name = "assigned_to", length = 128)
    private String assignedTo;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @Column(name = "resolved_at")
    private LocalDateTime resolvedAt;

    @Column(name = "ml_response", columnDefinition = "TEXT")
    private String mlResponse;

    @Column(name = "policy_decisions", columnDefinition = "TEXT")
    private String policyDecisions;

    @Column(name = "accounts_analyzed")
    private Integer accountsAnalyzed;

    @Column(name = "accounts_flagged")
    private Integer accountsFlagged;

    @Column(name = "risk_level", length = 16)
    private String severityLevel;

    @Column(name = "supervisor", length = 128)
    private String supervisor;

    @Column(name = "complaint_amount")
    private Double complaintAmount;

    @Column(name = "recovery_estimate")
    private Double recoveryEstimate;

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

    public String getRiskLevel() { return severityLevel; }
    public void setRiskLevel(String riskLevel) { this.severityLevel = riskLevel; }

    public String getSupervisor() { return supervisor; }
    public void setSupervisor(String supervisor) { this.supervisor = supervisor; }

    public Double getComplaintAmount() { return complaintAmount; }
    public void setComplaintAmount(Double complaintAmount) { this.complaintAmount = complaintAmount; }

    public Double getRecoveryEstimate() { return recoveryEstimate; }
    public void setRecoveryEstimate(Double recoveryEstimate) { this.recoveryEstimate = recoveryEstimate; }
}
