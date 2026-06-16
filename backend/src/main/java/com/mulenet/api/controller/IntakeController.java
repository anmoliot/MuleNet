package com.mulenet.api.controller;

import com.mulenet.api.dto.IntakeRequest;
import com.mulenet.api.dto.CaseResponse;
import com.mulenet.api.model.Case;
import com.mulenet.api.model.Complaint;
import com.mulenet.api.model.Transaction;
import com.mulenet.api.model.AuditLog;
import com.mulenet.api.repository.ComplaintRepository;
import com.mulenet.api.repository.TransactionRepository;
import com.mulenet.api.repository.AuditLogRepository;
import com.mulenet.api.service.MlService;
import com.mulenet.api.service.PolicyEngine;
import com.mulenet.api.service.NotificationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/intake")
@CrossOrigin(origins = "*")
public class IntakeController {

    @Autowired
    private ComplaintRepository complaintRepository;

    @Autowired
    private TransactionRepository transactionRepository;

    @Autowired
    private AuditLogRepository auditLogRepository;

    @Autowired
    private MlService mlService;

    @Autowired
    private PolicyEngine policyEngine;

    @Autowired
    private NotificationService notificationService;

    private String getUsername() {
        return SecurityContextHolder.getContext().getAuthentication().getName();
    }

    private String getRole() {
        return SecurityContextHolder.getContext().getAuthentication().getAuthorities().stream()
                .map(a -> a.getAuthority().replace("ROLE_", ""))
                .findFirst().orElse("UNKNOWN");
    }

    @PostMapping
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR', 'FRAUD_ADMIN')")
    public ResponseEntity<?> processIntake(@jakarta.validation.Valid @RequestBody IntakeRequest request) {
        // 1. Save Complaint
        String complaintId = null;
        if (request.getComplaint() != null) {
            complaintRepository.save(request.getComplaint());
            complaintId = request.getComplaint().getComplaintId();
        }

        // 2. Save Transactions
        if (request.getTransactions() != null && !request.getTransactions().isEmpty()) {
            transactionRepository.saveAll(request.getTransactions());
        }

        // 3. Call ML Service to analyze the graph
        String mlResponse = mlService.analyzeGraph(request);

        // 4. Layer 7 — Process through Policy Engine, create Case
        Case fraudCase = policyEngine.processAnalysis(mlResponse, complaintId);

        // Publish live push notifications for high-risk ingestions
        if (fraudCase.getRiskScore() >= 60.0) {
            notificationService.broadcast(
                "Critical Fraud Flagged", 
                "Case " + fraudCase.getCaseId() + " has been auto-flagged with a risk score of " + String.format("%.1f", fraudCase.getRiskScore()) + "%. Immediate review required.",
                "HIGH"
            );
        } else if (fraudCase.getRiskScore() >= 40.0) {
            notificationService.broadcast(
                "Medium Risk Account Ingested", 
                "Case " + fraudCase.getCaseId() + " flagged with risk score (" + String.format("%.1f", fraudCase.getRiskScore()) + "%). Added to queue.",
                "MEDIUM"
            );
        }

        // 5. Audit the intake event
        auditLogRepository.save(new AuditLog(
                getUsername(),
                getRole(),
                "CASE_INTAKE",
                "Processed intake and initialized case " + fraudCase.getCaseId() + " for complaint " + complaintId + ". High risk score: " + fraudCase.getRiskScore(),
                null
        ));

        // 6. Return enriched case response
        CaseResponse caseResponse = CaseResponse.fromCase(fraudCase);
        return ResponseEntity.ok(caseResponse);
    }
}
