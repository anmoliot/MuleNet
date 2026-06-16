package com.mulenet.api.controller;

import com.mulenet.api.dto.IntakeRequest;
import com.mulenet.api.dto.CaseResponse;
import com.mulenet.api.model.Case;
import com.mulenet.api.model.Complaint;
import com.mulenet.api.model.Transaction;
import com.mulenet.api.repository.ComplaintRepository;
import com.mulenet.api.repository.TransactionRepository;
import com.mulenet.api.service.MlService;
import com.mulenet.api.service.PolicyEngine;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
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
    private MlService mlService;

    @Autowired
    private PolicyEngine policyEngine;

    @PostMapping
    public ResponseEntity<?> processIntake(@RequestBody IntakeRequest request) {
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

        // 5. Return enriched case response
        CaseResponse caseResponse = CaseResponse.fromCase(fraudCase);
        return ResponseEntity.ok(caseResponse);
    }
}
