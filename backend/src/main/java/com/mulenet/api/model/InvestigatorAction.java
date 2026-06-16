package com.mulenet.api.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "investigator_actions")
public class InvestigatorAction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String caseId;

    private String accountId;

    @Enumerated(EnumType.STRING)
    private ActionType action;

    @Column(columnDefinition = "CLOB")
    private String rationale;

    private String performedBy;

    private LocalDateTime timestamp;

    private Double riskScoreAtAction;

    public InvestigatorAction() {
        this.timestamp = LocalDateTime.now();
    }

    public enum ActionType {
        FREEZE_IMMEDIATE, SOFT_HOLD, STEP_UP_MONITOR, MONITOR,
        ESCALATE, DISMISS, ADD_NOTE, REASSIGN, CLOSE
    }

    // Getters and Setters

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getCaseId() { return caseId; }
    public void setCaseId(String caseId) { this.caseId = caseId; }

    public String getAccountId() { return accountId; }
    public void setAccountId(String accountId) { this.accountId = accountId; }

    public ActionType getAction() { return action; }
    public void setAction(ActionType action) { this.action = action; }

    public String getRationale() { return rationale; }
    public void setRationale(String rationale) { this.rationale = rationale; }

    public String getPerformedBy() { return performedBy; }
    public void setPerformedBy(String performedBy) { this.performedBy = performedBy; }

    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }

    public Double getRiskScoreAtAction() { return riskScoreAtAction; }
    public void setRiskScoreAtAction(Double riskScoreAtAction) { this.riskScoreAtAction = riskScoreAtAction; }
}
