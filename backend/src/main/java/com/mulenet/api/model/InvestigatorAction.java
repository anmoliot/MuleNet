package com.mulenet.api.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "investigator_actions")
public class InvestigatorAction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "case_id", nullable = false, length = 64)
    private String caseId;

    @Column(name = "account_id", length = 64)
    private String accountId;

    @Enumerated(EnumType.STRING)
    @Column(length = 64)
    private ActionType action;

    @Column(name = "rationale", columnDefinition = "TEXT")
    private String rationale;

    @Column(name = "performed_by", length = 128)
    private String performedBy;

    @Column(name = "timestamp")
    private LocalDateTime timestamp;

    @Column(name = "risk_score_at_action")
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
