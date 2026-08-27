package com.mulenet.api.service;

import com.mulenet.api.model.Case;
import com.mulenet.api.model.InvestigatorAction;
import com.mulenet.api.model.PolicyConfig;
import com.mulenet.api.repository.CaseRepository;
import com.mulenet.api.repository.InvestigatorActionRepository;
import com.mulenet.api.repository.PolicyConfigRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.Optional;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

public class PolicyEngineTest {

    @Mock
    private CaseRepository caseRepository;

    @Mock
    private InvestigatorActionRepository actionRepository;

    @Mock
    private PolicyConfigRepository configRepository;

    @InjectMocks
    private PolicyEngine policyEngine;

    @BeforeEach
    public void setup() {
        MockitoAnnotations.openMocks(this);
        when(configRepository.findById(anyString())).thenReturn(Optional.empty());
        policyEngine.init();
    }

    @Test
    public void testProcessAnalysis_HighRisk() {
        String mlResponseJson = "{ \"recovery_ranking\": [ { \"account_id\": \"ACC1\", \"composite_score\": 85.0 } ] }";
        
        when(caseRepository.save(any(Case.class))).thenAnswer(i -> i.getArguments()[0]);

        Case fraudCase = policyEngine.processAnalysis(mlResponseJson, "COMPLAINT-1");

        assertNotNull(fraudCase);
        assertEquals(85.0, fraudCase.getRiskScore());
        assertEquals(Case.CaseStatus.INVESTIGATING, fraudCase.getStatus());
        assertEquals("CRITICAL", fraudCase.getSeverityLevel());
        assertTrue(fraudCase.getPolicyDecisions().contains("FREEZE_IMMEDIATE"));
    }

    @Test
    public void testProcessAnalysis_LowRisk() {
        String mlResponseJson = "{ \"recovery_ranking\": [ { \"account_id\": \"ACC1\", \"composite_score\": 15.0 } ] }";
        
        when(caseRepository.save(any(Case.class))).thenAnswer(i -> i.getArguments()[0]);

        Case fraudCase = policyEngine.processAnalysis(mlResponseJson, "COMPLAINT-1");

        assertNotNull(fraudCase);
        assertEquals(15.0, fraudCase.getRiskScore());
        assertEquals(Case.CaseStatus.OPEN, fraudCase.getStatus());
        assertEquals("INFO", fraudCase.getSeverityLevel());
        assertTrue(fraudCase.getPolicyDecisions().contains("MONITOR"));
    }

    @Test
    public void testRecordAction() {
        Case dummyCase = new Case();
        dummyCase.setCaseId("CASE-123");
        dummyCase.setRiskScore(60.0);
        dummyCase.setStatus(Case.CaseStatus.OPEN);

        when(caseRepository.findByCaseId("CASE-123")).thenReturn(Optional.of(dummyCase));
        when(actionRepository.save(any(InvestigatorAction.class))).thenAnswer(i -> i.getArguments()[0]);

        InvestigatorAction action = policyEngine.recordAction("CASE-123", "ACC1", InvestigatorAction.ActionType.FREEZE_IMMEDIATE, "Test rationale", "Admin");

        assertNotNull(action);
        assertEquals("CASE-123", action.getCaseId());
        assertEquals(InvestigatorAction.ActionType.FREEZE_IMMEDIATE, action.getAction());
        assertEquals(Case.CaseStatus.FROZEN, dummyCase.getStatus());
    }

    @Test
    public void testUpdateThresholds() {
        policyEngine.updateThresholds(Map.of("freeze_threshold", 85.0));
        Map<String, Double> thresholds = policyEngine.getThresholds();
        assertEquals(85.0, thresholds.get("freeze_threshold"));
        verify(configRepository, times(1)).save(any(PolicyConfig.class));
    }
}
