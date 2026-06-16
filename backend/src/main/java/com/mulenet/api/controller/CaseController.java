package com.mulenet.api.controller;

import com.mulenet.api.dto.ActionRequest;
import com.mulenet.api.dto.CaseResponse;
import com.mulenet.api.model.Case;
import com.mulenet.api.model.InvestigatorAction;
import com.mulenet.api.model.AuditLog;
import com.mulenet.api.repository.CaseRepository;
import com.mulenet.api.repository.InvestigatorActionRepository;
import com.mulenet.api.repository.AuditLogRepository;
import com.mulenet.api.service.PolicyEngine;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/cases")
@CrossOrigin(origins = "*")
public class CaseController {

    @Autowired
    private CaseRepository caseRepository;

    @Autowired
    private InvestigatorActionRepository actionRepository;

    @Autowired
    private AuditLogRepository auditLogRepository;

    @Autowired
    private PolicyEngine policyEngine;

    private String getUsername() {
        return SecurityContextHolder.getContext().getAuthentication().getName();
    }

    private String getRole() {
        return SecurityContextHolder.getContext().getAuthentication().getAuthorities().stream()
                .map(a -> a.getAuthority().replace("ROLE_", ""))
                .findFirst().orElse("UNKNOWN");
    }

    /**
     * GET /api/cases — list all cases, newest first.
     */
    @GetMapping
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR', 'FRAUD_ADMIN', 'COMPLIANCE_OFFICER')")
    public ResponseEntity<List<CaseResponse>> listCases(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String severityLevel,
            @RequestParam(required = false) String assignedTo,
            @RequestParam(required = false) Double minRisk,
            @RequestParam(required = false) String query) {

        List<Case> cases = caseRepository.findAllByOrderByCreatedAtDesc();

        List<CaseResponse> responses = cases.stream()
                .map(CaseResponse::fromCase)
                .filter(c -> {
                    if (status != null && !status.isEmpty() && !status.equalsIgnoreCase(c.getStatus())) {
                        return false;
                    }
                    if (severityLevel != null && !severityLevel.isEmpty() && !severityLevel.equalsIgnoreCase(c.getSeverityLevel())) {
                        return false;
                    }
                    if (assignedTo != null && !assignedTo.isEmpty()) {
                        if (c.getAssignedTo() == null || !c.getAssignedTo().equalsIgnoreCase(assignedTo)) {
                            return false;
                        }
                    }
                    if (minRisk != null && c.getRiskScore() < minRisk) {
                        return false;
                    }
                    if (query != null && !query.isEmpty()) {
                        String q = query.toLowerCase();
                        boolean matchCaseId = c.getCaseId() != null && c.getCaseId().toLowerCase().contains(q);
                        boolean matchCompId = c.getComplaintId() != null && c.getComplaintId().toLowerCase().contains(q);
                        return matchCaseId || matchCompId;
                    }
                    return true;
                })
                .collect(Collectors.toList());

        return ResponseEntity.ok(responses);
    }

    /**
     * GET /api/cases/{caseId} — full case detail with action history.
     */
    @GetMapping("/{caseId}")
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR', 'FRAUD_ADMIN', 'COMPLIANCE_OFFICER')")
    public ResponseEntity<?> getCase(@PathVariable String caseId) {
        return caseRepository.findByCaseId(caseId)
                .map(c -> {
                    CaseResponse response = CaseResponse.fromCase(c);
                    List<InvestigatorAction> actions =
                            actionRepository.findByCaseIdOrderByTimestampDesc(caseId);
                    response.setActionHistory(actions);
                    return ResponseEntity.ok(response);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * POST /api/cases/{caseId}/actions — record an investigator action.
     */
    @PostMapping("/{caseId}/actions")
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR')")
    public ResponseEntity<?> recordAction(
            @PathVariable String caseId,
            @jakarta.validation.Valid @RequestBody ActionRequest request) {

        if (caseRepository.findByCaseId(caseId).isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        InvestigatorAction action = policyEngine.recordAction(
                caseId,
                request.getAccountId(),
                request.getAction(),
                request.getRationale(),
                request.getPerformedBy()
        );

        // Audit the action
        auditLogRepository.save(new AuditLog(
                getUsername(),
                getRole(),
                "INVESTIGATOR_ACTION",
                "Executed action " + request.getAction() + " on account " + request.getAccountId() + " for case " + caseId + ". Rationale: " + request.getRationale(),
                null
        ));

        return ResponseEntity.ok(action);
    }

    /**
     * PUT /api/cases/{caseId}/status — update case status directly.
     */
    @PutMapping("/{caseId}/status")
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR')")
    public ResponseEntity<?> updateStatus(
            @PathVariable String caseId,
            @RequestBody Map<String, String> body) {

        return caseRepository.findByCaseId(caseId)
                .map(c -> {
                    try {
                        String oldStatus = c.getStatus().name();
                        String newStatus = body.get("status");
                        c.setStatus(Case.CaseStatus.valueOf(newStatus));
                        caseRepository.save(c);

                        // Audit status override
                        auditLogRepository.save(new AuditLog(
                                getUsername(),
                                getRole(),
                                "CASE_STATUS_OVERRIDE",
                                "Changed case " + caseId + " status from " + oldStatus + " to " + newStatus,
                                null
                        ));

                        return ResponseEntity.ok(CaseResponse.fromCase(c));
                    } catch (IllegalArgumentException e) {
                        return ResponseEntity.badRequest().body("Invalid status: " + body.get("status"));
                    }
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * GET /api/policy/thresholds — current policy thresholds.
     */
    @GetMapping("/policy/thresholds")
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR', 'FRAUD_ADMIN', 'COMPLIANCE_OFFICER')")
    public ResponseEntity<Map<String, Double>> getThresholds() {
        return ResponseEntity.ok(policyEngine.getThresholds());
    }

    /**
     * PUT /api/policy/thresholds — update policy thresholds.
     */
    @PutMapping("/policy/thresholds")
    @PreAuthorize("hasRole('FRAUD_ADMIN')")
    public ResponseEntity<Map<String, Double>> updateThresholds(
            @RequestBody Map<String, Double> thresholds) {
        
        Map<String, Double> oldThresholds = policyEngine.getThresholds();
        policyEngine.updateThresholds(thresholds);
        Map<String, Double> newThresholds = policyEngine.getThresholds();

        // Audit the change
        auditLogRepository.save(new AuditLog(
                getUsername(),
                getRole(),
                "POLICY_THRESHOLD_UPDATE",
                "Updated thresholds: " + thresholds.keySet().stream()
                    .map(k -> k + " (" + oldThresholds.get(k) + " -> " + newThresholds.get(k) + ")")
                    .collect(Collectors.joining(", ")),
                null
        ));

        return ResponseEntity.ok(policyEngine.getThresholds());
    }

    /**
     * GET /api/cases/stats — dashboard summary statistics.
     */
    @GetMapping("/stats/summary")
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR', 'FRAUD_ADMIN', 'COMPLIANCE_OFFICER')")
    public ResponseEntity<Map<String, Object>> getStats() {
        List<Case> allCases = caseRepository.findAll();

        long totalCases = allCases.size();
        long openCases = allCases.stream()
                .filter(c -> c.getStatus() == Case.CaseStatus.OPEN
                        || c.getStatus() == Case.CaseStatus.INVESTIGATING)
                .count();
        long criticalCases = allCases.stream()
                .filter(c -> "CRITICAL".equals(c.getSeverityLevel()))
                .count();
        long frozenCases = allCases.stream()
                .filter(c -> c.getStatus() == Case.CaseStatus.FROZEN)
                .count();
        double avgRisk = allCases.stream()
                .filter(c -> c.getRiskScore() != null)
                .mapToDouble(Case::getRiskScore)
                .average()
                .orElse(0.0);

        return ResponseEntity.ok(Map.of(
                "total_cases", totalCases,
                "active_cases", openCases,
                "critical_alerts", criticalCases,
                "frozen_accounts", frozenCases,
                "avg_risk_score", Math.round(avgRisk * 100.0) / 100.0
        ));
    }

    /**
     * GET /api/cases/feedback — get all resolved cases for model retraining feedback.
     */
    @GetMapping("/feedback")
    @PreAuthorize("hasRole('FRAUD_ADMIN')")
    public ResponseEntity<List<Case>> getCasesFeedback() {
        List<Case> cases = caseRepository.findAll().stream()
                .filter(c -> c.getStatus() == Case.CaseStatus.CLOSED 
                          || c.getStatus() == Case.CaseStatus.FROZEN 
                          || c.getStatus() == Case.CaseStatus.DISMISSED)
                .collect(Collectors.toList());
        return ResponseEntity.ok(cases);
    }

    /**
     * PUT /api/cases/{caseId}/assign — assign investigator to case.
     */
    @PutMapping("/{caseId}/assign")
    @PreAuthorize("hasAnyRole('SUPERVISOR', 'FRAUD_ADMIN')")
    public ResponseEntity<?> assignCase(
            @PathVariable String caseId,
            @RequestBody Map<String, String> body) {

        String username = body.get("assignedTo");
        if (username == null) {
            return ResponseEntity.badRequest().body(Map.of("message", "assignedTo is required"));
        }

        return caseRepository.findByCaseId(caseId)
                .map(c -> {
                    c.setAssignedTo(username);
                    if (c.getStatus() == Case.CaseStatus.OPEN) {
                        c.setStatus(Case.CaseStatus.INVESTIGATING);
                    }
                    caseRepository.save(c);

                    // Audit the assignment
                    auditLogRepository.save(new AuditLog(
                            getUsername(),
                            getRole(),
                            "CASE_ASSIGNMENT",
                            "Assigned case " + caseId + " to investigator " + username,
                            null
                    ));

                    return ResponseEntity.ok(CaseResponse.fromCase(c));
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
