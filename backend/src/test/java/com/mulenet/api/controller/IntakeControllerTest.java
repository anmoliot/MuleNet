package com.mulenet.api.controller;

import com.mulenet.api.dto.IntakeRequest;
import com.mulenet.api.model.Case;
import com.mulenet.api.model.Complaint;
import com.mulenet.api.model.Transaction;
import com.mulenet.api.repository.ComplaintRepository;
import com.mulenet.api.repository.TransactionRepository;
import com.mulenet.api.repository.AuditLogRepository;
import com.mulenet.api.repository.AccountRepository;
import com.mulenet.api.service.MlService;
import com.mulenet.api.service.PolicyEngine;
import com.mulenet.api.service.NotificationService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.Collections;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

public class IntakeControllerTest {

    @Mock private ComplaintRepository complaintRepository;
    @Mock private TransactionRepository transactionRepository;
    @Mock private AuditLogRepository auditLogRepository;
    @Mock private AccountRepository accountRepository;
    @Mock private MlService mlService;
    @Mock private PolicyEngine policyEngine;
    @Mock private NotificationService notificationService;
    @Mock private SecurityContext securityContext;
    @Mock private Authentication authentication;

    @InjectMocks
    private IntakeController intakeController;

    @BeforeEach
    public void setup() {
        MockitoAnnotations.openMocks(this);
        SecurityContextHolder.setContext(securityContext);
        when(securityContext.getAuthentication()).thenReturn(authentication);
        when(authentication.getName()).thenReturn("testuser");
        when(authentication.getAuthorities()).thenReturn(Collections.emptyList());
    }

    @Test
    public void testProcessIntake() {
        Complaint complaint = new Complaint();
        complaint.setComplaintId("COMP-123");

        Transaction txn = new Transaction();
        txn.setSenderAccount("SENDER");
        txn.setReceiverAccount("RECEIVER");

        IntakeRequest request = new IntakeRequest(complaint, Collections.singletonList(txn));

        when(accountRepository.findByAccountId(anyString())).thenReturn(Optional.empty());
        when(mlService.analyzeGraph(any(IntakeRequest.class))).thenReturn("{}");
        
        Case dummyCase = new Case();
        dummyCase.setCaseId("CASE-999");
        dummyCase.setRiskScore(75.0);
        
        when(policyEngine.processAnalysis(anyString(), anyString())).thenReturn(dummyCase);

        ResponseEntity<?> response = intakeController.processIntake(request);

        assertEquals(200, response.getStatusCode().value());
        assertNotNull(response.getBody());
        
        verify(accountRepository, times(2)).save(any());
        verify(complaintRepository, times(1)).save(any(Complaint.class));
        verify(transactionRepository, times(1)).saveAll(any());
        verify(mlService, times(1)).analyzeGraph(any(IntakeRequest.class));
        verify(policyEngine, times(1)).processAnalysis(anyString(), anyString());
        verify(notificationService, times(1)).broadcast(anyString(), anyString(), anyString());
        verify(auditLogRepository, times(1)).save(any());
    }
}
