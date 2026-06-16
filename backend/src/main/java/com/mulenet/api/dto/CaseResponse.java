package com.mulenet.api.dto;

import com.mulenet.api.model.Case;
import com.mulenet.api.model.InvestigatorAction;
import java.util.List;

/**
 * Structured response combining ML analysis + policy decisions + case metadata.
 */
public class CaseResponse {

    private String caseId;
    private String complaintId;
    private String status;
    private Double riskScore;
    private String severityLevel;
    private Integer accountsAnalyzed;
    private Integer accountsFlagged;
    private String createdAt;
    private String mlResponse;         // raw ML JSON
    private String policyDecisions;    // policy decisions JSON
    private List<InvestigatorAction> actionHistory;

    public CaseResponse() {}

    public static CaseResponse fromCase(Case c) {
        CaseResponse r = new CaseResponse();
        r.setCaseId(c.getCaseId());
        r.setComplaintId(c.getComplaintId());
        r.setStatus(c.getStatus().name());
        r.setRiskScore(c.getRiskScore());
        r.setSeverityLevel(c.getSeverityLevel());
        r.setAccountsAnalyzed(c.getAccountsAnalyzed());
        r.setAccountsFlagged(c.getAccountsFlagged());
        r.setCreatedAt(c.getCreatedAt() != null ? c.getCreatedAt().toString() : null);
        r.setMlResponse(c.getMlResponse());
        r.setPolicyDecisions(c.getPolicyDecisions());
        return r;
    }

    // Getters and Setters

    public String getCaseId() { return caseId; }
    public void setCaseId(String caseId) { this.caseId = caseId; }

    public String getComplaintId() { return complaintId; }
    public void setComplaintId(String complaintId) { this.complaintId = complaintId; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Double getRiskScore() { return riskScore; }
    public void setRiskScore(Double riskScore) { this.riskScore = riskScore; }

    public String getSeverityLevel() { return severityLevel; }
    public void setSeverityLevel(String severityLevel) { this.severityLevel = severityLevel; }

    public Integer getAccountsAnalyzed() { return accountsAnalyzed; }
    public void setAccountsAnalyzed(Integer accountsAnalyzed) { this.accountsAnalyzed = accountsAnalyzed; }

    public Integer getAccountsFlagged() { return accountsFlagged; }
    public void setAccountsFlagged(Integer accountsFlagged) { this.accountsFlagged = accountsFlagged; }

    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }

    public String getMlResponse() { return mlResponse; }
    public void setMlResponse(String mlResponse) { this.mlResponse = mlResponse; }

    public String getPolicyDecisions() { return policyDecisions; }
    public void setPolicyDecisions(String policyDecisions) { this.policyDecisions = policyDecisions; }

    public List<InvestigatorAction> getActionHistory() { return actionHistory; }
    public void setActionHistory(List<InvestigatorAction> actionHistory) { this.actionHistory = actionHistory; }
}
