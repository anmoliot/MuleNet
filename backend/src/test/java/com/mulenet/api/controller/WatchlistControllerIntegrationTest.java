package com.mulenet.api.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.mulenet.api.model.ExternalWatchlist;
import com.mulenet.api.repository.ExternalWatchlistRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
public class WatchlistControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ExternalWatchlistRepository watchlistRepository;

    @Autowired
    private ObjectMapper objectMapper;

    private String adminToken;
    private String investigatorToken;

    @BeforeEach
    public void setUp() throws Exception {
        // Authenticate as Admin
        Map<String, String> adminCreds = new HashMap<>();
        adminCreds.put("username", "admin");
        adminCreds.put("password", "password");

        MvcResult adminResult = mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(adminCreds)))
                .andExpect(status().isOk())
                .andReturn();

        String adminResponseJson = adminResult.getResponse().getContentAsString();
        Map<String, Object> adminMap = objectMapper.readValue(adminResponseJson, Map.class);
        this.adminToken = (String) adminMap.get("token");

        // Authenticate as Investigator
        Map<String, String> invCreds = new HashMap<>();
        invCreds.put("username", "investigator");
        invCreds.put("password", "password");

        MvcResult invResult = mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(invCreds)))
                .andExpect(status().isOk())
                .andReturn();

        String invResponseJson = invResult.getResponse().getContentAsString();
        Map<String, Object> invMap = objectMapper.readValue(invResponseJson, Map.class);
        this.investigatorToken = (String) invMap.get("token");
    }

    @Test
    public void testListAllWatchlistSuccess() throws Exception {
        mockMvc.perform(get("/api/external/watchlist/all")
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$.length()").value(6)); // Seeding puts 6 entries
    }

    @Test
    public void testAddWatchlistByAdminSuccess() throws Exception {
        ExternalWatchlist newEntry = new ExternalWatchlist(
                "AC-TEST-999",
                "I4C_SUSPECT_REGISTRY",
                30.0,
                "EXACT",
                0.99,
                "Integration Test Case Indicator"
        );

        MvcResult addResult = mockMvc.perform(post("/api/external/watchlist/add")
                .header("Authorization", "Bearer " + adminToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(newEntry)))
                .andExpect(status().isOk())
                .andReturn();

        String jsonResponse = addResult.getResponse().getContentAsString();
        ExternalWatchlist saved = objectMapper.readValue(jsonResponse, ExternalWatchlist.class);
        assertNotNull(saved.getId());
        assertEquals("AC-TEST-999", saved.getAccountId());
        assertEquals("account", saved.getIocType()); // derived value

        // Cleanup
        watchlistRepository.delete(saved);
    }

    @Test
    public void testAddWatchlistByInvestigatorForbidden() throws Exception {
        ExternalWatchlist newEntry = new ExternalWatchlist(
                "AC-TEST-888",
                "NCRP_FLAGGED",
                15.0,
                "EXACT",
                0.80,
                "Should fail because investigator is not FRAUD_ADMIN"
        );

        mockMvc.perform(post("/api/external/watchlist/add")
                .header("Authorization", "Bearer " + investigatorToken)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(newEntry)))
                .andExpect(status().isForbidden());
    }

    @Test
    public void testRemoveWatchlistByAdminSuccess() throws Exception {
        ExternalWatchlist testEntry = new ExternalWatchlist(
                "DEV-TEST-555",
                "DEVICE_BLACKLIST",
                20.0,
                "DEVICE_LINKED",
                0.95,
                "Delete Integration Test"
        );
        ExternalWatchlist saved = watchlistRepository.save(testEntry);

        mockMvc.perform(delete("/api/external/watchlist/remove/" + saved.getId())
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk());

        assertFalse(watchlistRepository.findById(saved.getId()).isPresent());
    }

    @Test
    public void testRemoveWatchlistByInvestigatorForbidden() throws Exception {
        ExternalWatchlist testEntry = new ExternalWatchlist(
                "DEV-TEST-666",
                "DEVICE_BLACKLIST",
                20.0,
                "DEVICE_LINKED",
                0.95,
                "Delete Investigator Test"
        );
        ExternalWatchlist saved = watchlistRepository.save(testEntry);

        try {
            mockMvc.perform(delete("/api/external/watchlist/remove/" + saved.getId())
                    .header("Authorization", "Bearer " + investigatorToken))
                    .andExpect(status().isForbidden());

            // Make sure it wasn't deleted
            assertTrue(watchlistRepository.findById(saved.getId()).isPresent());
        } finally {
            watchlistRepository.delete(testEntry);
        }
    }
}
