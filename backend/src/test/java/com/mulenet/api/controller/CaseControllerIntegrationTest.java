package com.mulenet.api.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.mulenet.api.model.Case;
import com.mulenet.api.model.User;
import com.mulenet.api.repository.CaseCommentRepository;
import com.mulenet.api.repository.CaseRepository;
import com.mulenet.api.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
public class CaseControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private CaseRepository caseRepository;

    @Autowired
    private CaseCommentRepository caseCommentRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private ObjectMapper objectMapper;

    private String adminToken;
    private String investigatorToken;
    private String supervisorToken;
    private String complianceToken;

    private Case testCase;

    @BeforeEach
    public void setUp() throws Exception {
        // Authenticate all users
        adminToken = obtainToken("admin");
        investigatorToken = obtainToken("investigator");
        supervisorToken = obtainToken("supervisor");
        complianceToken = obtainToken("compliance");

        // Seed a test case
        caseRepository.deleteAll();
        testCase = new Case();
        testCase.setCaseId("CASE-TEST-123");
        testCase.setComplaintId("COMP-9999");
        testCase.setStatus(Case.CaseStatus.OPEN);
        testCase.setRiskScore(75.5);
        testCase.setRiskLevel("HIGH");
        testCase.setSeverityLevel("HIGH");
        testCase.setAccountsAnalyzed(3);
        testCase.setAccountsFlagged(1);
        testCase = caseRepository.save(testCase);
    }

    private String obtainToken(String username) throws Exception {
        Map<String, String> credentials = new HashMap<>();
        credentials.put("username", username);
        credentials.put("password", "password");

        MvcResult result = mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(credentials)))
                .andExpect(status().isOk())
                .andReturn();

        String responseJson = result.getResponse().getContentAsString();
        Map<String, Object> responseMap = objectMapper.readValue(responseJson, Map.class);
        return (String) responseMap.get("token");
    }

    @Test
    public void testListCasesSuccess() throws Exception {
        mockMvc.perform(get("/api/cases")
                .header("Authorization", "Bearer " + investigatorToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$.length()").value(1));
    }

    @Test
    public void testExportCasesCsvAllowedRoles() throws Exception {
        // Supervisor allowed
        mockMvc.perform(get("/api/cases/export/csv")
                .header("Authorization", "Bearer " + supervisorToken))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith("text/csv"))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("CASE-TEST-123")));

        // Compliance allowed
        mockMvc.perform(get("/api/cases/export/csv")
                .header("Authorization", "Bearer " + complianceToken))
                .andExpect(status().isOk());

        // Investigator forbidden
        mockMvc.perform(get("/api/cases/export/csv")
                .header("Authorization", "Bearer " + investigatorToken))
                .andExpect(status().isForbidden());
    }

    @Test
    public void testCaseCommentsWorkflow() throws Exception {
        // Add a comment
        Map<String, String> commentReq = new HashMap<>();
        commentReq.put("commentText", "This is an investigator comment");

        mockMvc.perform(post("/api/cases/CASE-TEST-123/comments")
                .header("Authorization", "Bearer " + investigatorToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(commentReq)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("investigator"))
                .andExpect(jsonPath("$.commentText").value("This is an investigator comment"));

        // Get comments
        mockMvc.perform(get("/api/cases/CASE-TEST-123/comments")
                .header("Authorization", "Bearer " + investigatorToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].commentText").value("This is an investigator comment"));
    }

    @Test
    public void testAdminUserManagement() throws Exception {
        // List users as Admin - Success
        mockMvc.perform(get("/api/users")
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$[0].password").isEmpty()); // checks that password hash is nullified

        // List users as non-Admin - Forbidden
        mockMvc.perform(get("/api/users")
                .header("Authorization", "Bearer " + supervisorToken))
                .andExpect(status().isForbidden());

        // Toggle user status as Admin
        Map<String, Object> statusReq = new HashMap<>();
        statusReq.put("isActive", false);

        mockMvc.perform(put("/api/users/investigator/status")
                .header("Authorization", "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(statusReq)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.isActive").value(false));

        // Assert update in DB
        User updated = userRepository.findByUsername("investigator").orElseThrow();
        assertFalse(updated.getIsActive());

        // Cleanup: restore status
        updated.setIsActive(true);
        userRepository.save(updated);

        // Toggle own status as Admin - Bad Request
        statusReq.put("isActive", false);
        mockMvc.perform(put("/api/users/admin/status")
                .header("Authorization", "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(statusReq)))
                .andExpect(status().isBadRequest());
    }

    @Test
    public void testPolicyThresholdCRUD() throws Exception {
        // Get thresholds
        mockMvc.perform(get("/api/cases/policy/thresholds")
                .header("Authorization", "Bearer " + investigatorToken))
                .andExpect(status().isOk());

        // Update thresholds as Admin - Success
        Map<String, Double> newThresholds = new HashMap<>();
        newThresholds.put("freeze_threshold", 85.0);

        mockMvc.perform(put("/api/cases/policy/thresholds")
                .header("Authorization", "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(newThresholds)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.freeze_threshold").value(85.0));

        // Update thresholds as Supervisor - Forbidden
        mockMvc.perform(put("/api/cases/policy/thresholds")
                .header("Authorization", "Bearer " + supervisorToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(newThresholds)))
                .andExpect(status().isForbidden());
    }
}
