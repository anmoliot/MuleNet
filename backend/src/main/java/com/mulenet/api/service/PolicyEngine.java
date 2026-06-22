package com.mulenet.api.service;

import com.mulenet.api.model.Case;
import com.mulenet.api.model.InvestigatorAction;
import com.mulenet.api.model.PolicyConfig;
import com.mulenet.api.repository.CaseRepository;
import com.mulenet.api.repository.InvestigatorActionRepository;
import com.mulenet.api.repository.PolicyConfigRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import jakarta.annotation.PostConstruct;

import java.time.LocalDateTime;
import java.util.*;

/**
 * Layer 7 — Policy & Intervention Engine
 *
 * Translates ML risk scores into actionable policy decisions.
 * Configurable thresholds, audit logging, and intervention orchestration.
 */
@Service
public class PolicyEngine {

    // Configurable thresholds (Layer 6 fusion → Layer 7 policy)
    private double freezeThreshold = 70.0;
    private double softHoldThreshold = 50.0;
    private double escalationThreshold = 60.0;
    private double monitorThreshold = 25.0;

    private final ObjectMapper mapper = new ObjectMapper();

    @Autowired
    private CaseRepository caseRepository;

    @Autowired
    private InvestigatorActionRepository actionRepository;

    @Autowired
    private PolicyConfigRepository configRepository;

    @PostConstruct
    public void init() {
        freezeThreshold = getOrSaveDefault("freeze_threshold", 70.0);
        softHoldThreshold = getOrSaveDefault("soft_hold_threshold", 50.0);
        escalationThreshold = getOrSaveDefault("escalation_threshold", 60.0);
        monitorThreshold = getOrSaveDefault("monitor_threshold", 25.0);
    }

    private double getOrSaveDefault(String key, double defaultValue) {
        try {
            return configRepository.findById(key)
                    .map(PolicyConfig::getConfigValue)
                    .orElseGet(() -> {
                        configRepository.save(new PolicyConfig(key, defaultValue));
                        return defaultValue;
                    });
        } catch (Exception e) {
            // Fallback for tests or bootstrapping
            return defaultValue;
        }
    }

    /**
     * Process ML response and generate policy decisions.
     * Creates a Case record and returns enriched response.
     */
    public Case processAnalysis(String mlResponseJson, String complaintId) {
        Case fraudCase = new Case();
        fraudCase.setCaseId("CASE-" + System.currentTimeMillis());
        fraudCase.setComplaintId(complaintId);
        fraudCase.setMlResponse(mlResponseJson);
        fraudCase.setStatus(Case.CaseStatus.OPEN);

        try {
            JsonNode ml = mapper.readTree(mlResponseJson);

            // Extract top risk score from recovery ranking
            double maxRisk = 0.0;
            int flagged = 0;
            int analyzed = 0;

            if (ml.has("recovery_ranking")) {
                ArrayNode ranking = (ArrayNode) ml.get("recovery_ranking");
                analyzed = ranking.size();
                for (JsonNode item : ranking) {
                    double score = item.get("composite_score").asDouble(0);
                    if (score > maxRisk) maxRisk = score;
                    if (score >= monitorThreshold) flagged++;
                }
            }

            fraudCase.setRiskScore(maxRisk);
            fraudCase.setAccountsAnalyzed(analyzed);
            fraudCase.setAccountsFlagged(flagged);
            fraudCase.setSeverityLevel(computeSeverity(maxRisk));

            // Generate policy decisions
            String policyJson = generatePolicyDecisions(ml);
            fraudCase.setPolicyDecisions(policyJson);

            // Auto-escalate critical cases
            if (maxRisk >= freezeThreshold) {
                fraudCase.setStatus(Case.CaseStatus.INVESTIGATING);
            }

        } catch (Exception e) {
            fraudCase.setRiskScore(0.0);
            fraudCase.setSeverityLevel("UNKNOWN");
        }

        return caseRepository.save(fraudCase);
    }

    /**
     * Generate structured policy decisions from ML output.
     */
    private String generatePolicyDecisions(JsonNode ml) {
        try {
            ArrayNode decisions = mapper.createArrayNode();

            if (ml.has("recovery_ranking")) {
                for (JsonNode item : ml.get("recovery_ranking")) {
                    double score = item.get("composite_score").asDouble(0);
                    String accountId = item.get("account_id").asText();

                    ObjectNode decision = mapper.createObjectNode();
                    decision.put("account_id", accountId);
                    decision.put("composite_score", score);
                    decision.put("policy_action", determineAction(score));
                    decision.put("priority", determinePriority(score));
                    decision.put("sla_minutes", determineSla(score));
                    decision.put("auto_executable", score >= freezeThreshold);
                    decision.put("requires_approval", score >= softHoldThreshold && score < freezeThreshold);
                    decisions.add(decision);
                }
            }

            return mapper.writeValueAsString(decisions);
        } catch (Exception e) {
            return "[]";
        }
    }

    private String determineAction(double score) {
        if (score >= freezeThreshold) return "FREEZE_IMMEDIATE";
        if (score >= escalationThreshold) return "ESCALATE";
        if (score >= softHoldThreshold) return "SOFT_HOLD";
        if (score >= monitorThreshold) return "STEP_UP_MONITOR";
        return "MONITOR";
    }

    private String determinePriority(double score) {
        if (score >= freezeThreshold) return "P1_CRITICAL";
        if (score >= escalationThreshold) return "P2_HIGH";
        if (score >= softHoldThreshold) return "P3_MEDIUM";
        return "P4_LOW";
    }

    private int determineSla(double score) {
        if (score >= freezeThreshold) return 5;      // 5 minutes
        if (score >= escalationThreshold) return 15;  // 15 minutes
        if (score >= softHoldThreshold) return 60;    // 1 hour
        return 1440;                                   // 24 hours
    }

    private String computeSeverity(double score) {
        if (score >= 80) return "CRITICAL";
        if (score >= 60) return "HIGH";
        if (score >= 40) return "MEDIUM";
        if (score >= 20) return "LOW";
        return "INFO";
    }

    /**
     * Record an investigator action against a case.
     */
    public InvestigatorAction recordAction(String caseId, String accountId,
                                           InvestigatorAction.ActionType actionType,
                                           String rationale, String performedBy) {
        InvestigatorAction action = new InvestigatorAction();
        action.setCaseId(caseId);
        action.setAccountId(accountId);
        action.setAction(actionType);
        action.setRationale(rationale);
        action.setPerformedBy(performedBy);

        // Update case status based on action
        caseRepository.findByCaseId(caseId).ifPresent(c -> {
            switch (actionType) {
                case FREEZE_IMMEDIATE:
                    c.setStatus(Case.CaseStatus.FROZEN);
                    action.setRiskScoreAtAction(c.getRiskScore());
                    break;
                case ESCALATE:
                    c.setStatus(Case.CaseStatus.ESCALATED);
                    break;
                case DISMISS:
                    c.setStatus(Case.CaseStatus.DISMISSED);
                    c.setResolvedAt(LocalDateTime.now());
                    break;
                case CLOSE:
                    c.setStatus(Case.CaseStatus.CLOSED);
                    c.setResolvedAt(LocalDateTime.now());
                    break;
                default:
                    break;
            }
            caseRepository.save(c);
        });

        return actionRepository.save(action);
    }

    /**
     * Get current policy thresholds (for frontend config UI).
     */
    public Map<String, Double> getThresholds() {
        Map<String, Double> thresholds = new LinkedHashMap<>();
        thresholds.put("freeze_threshold", freezeThreshold);
        thresholds.put("soft_hold_threshold", softHoldThreshold);
        thresholds.put("escalation_threshold", escalationThreshold);
        thresholds.put("monitor_threshold", monitorThreshold);
        return thresholds;
    }

    /**
     * Update policy thresholds.
     */
    public void updateThresholds(Map<String, Double> newThresholds) {
        if (newThresholds.containsKey("freeze_threshold")) {
            this.freezeThreshold = newThresholds.get("freeze_threshold");
            configRepository.save(new PolicyConfig("freeze_threshold", this.freezeThreshold));
        }
        if (newThresholds.containsKey("soft_hold_threshold")) {
            this.softHoldThreshold = newThresholds.get("soft_hold_threshold");
            configRepository.save(new PolicyConfig("soft_hold_threshold", this.softHoldThreshold));
        }
        if (newThresholds.containsKey("escalation_threshold")) {
            this.escalationThreshold = newThresholds.get("escalation_threshold");
            configRepository.save(new PolicyConfig("escalation_threshold", this.escalationThreshold));
        }
        if (newThresholds.containsKey("monitor_threshold")) {
            this.monitorThreshold = newThresholds.get("monitor_threshold");
            configRepository.save(new PolicyConfig("monitor_threshold", this.monitorThreshold));
        }
    }
}
