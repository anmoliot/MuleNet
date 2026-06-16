package com.mulenet.api.controller;

import com.mulenet.api.dto.ActionRequest;
import com.mulenet.api.dto.CaseResponse;
import com.mulenet.api.model.Case;
import com.mulenet.api.model.InvestigatorAction;
import com.mulenet.api.repository.CaseRepository;
import com.mulenet.api.repository.InvestigatorActionRepository;
import com.mulenet.api.service.PolicyEngine;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
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
    private PolicyEngine policyEngine;

    /**
     * GET /api/cases — list all cases, newest first.
     */
    @GetMapping
    public ResponseEntity<List<CaseResponse>> listCases(
            @RequestParam(required = false) String status) {

        List<Case> cases;
        if (status != null && !status.isEmpty()) {
            try {
                cases = caseRepository.findByStatus(Case.CaseStatus.valueOf(status));
            } catch (IllegalArgumentException e) {
                cases = caseRepository.findAllByOrderByCreatedAtDesc();
            }
        } else {
            cases = caseRepository.findAllByOrderByCreatedAtDesc();
        }

        List<CaseResponse> responses = cases.stream()
                .map(CaseResponse::fromCase)
                .collect(Collectors.toList());

        return ResponseEntity.ok(responses);
    }

    /**
     * GET /api/cases/{caseId} — full case detail with action history.
     */
    @GetMapping("/{caseId}")
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
    public ResponseEntity<?> recordAction(
            @PathVariable String caseId,
            @RequestBody ActionRequest request) {

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

        return ResponseEntity.ok(action);
    }

    /**
     * PUT /api/cases/{caseId}/status — update case status directly.
     */
    @PutMapping("/{caseId}/status")
    public ResponseEntity<?> updateStatus(
            @PathVariable String caseId,
            @RequestBody Map<String, String> body) {

        return caseRepository.findByCaseId(caseId)
                .map(c -> {
                    try {
                        c.setStatus(Case.CaseStatus.valueOf(body.get("status")));
                        caseRepository.save(c);
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
    public ResponseEntity<Map<String, Double>> getThresholds() {
        return ResponseEntity.ok(policyEngine.getThresholds());
    }

    /**
     * PUT /api/policy/thresholds — update policy thresholds.
     */
    @PutMapping("/policy/thresholds")
    public ResponseEntity<Map<String, Double>> updateThresholds(
            @RequestBody Map<String, Double> thresholds) {
        policyEngine.updateThresholds(thresholds);
        return ResponseEntity.ok(policyEngine.getThresholds());
    }

    /**
     * GET /api/cases/stats — dashboard summary statistics.
     */
    @GetMapping("/stats/summary")
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
}
