package com.mulenet.api.service;

import com.mulenet.api.dto.IntakeRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

public class MlServiceTest {

    @Mock
    private RestTemplate restTemplate;

    @InjectMocks
    private MlService mlService;

    @BeforeEach
    public void setup() {
        MockitoAnnotations.openMocks(this);
        ReflectionTestUtils.setField(mlService, "mlServiceUrl", "http://localhost:8000/api/analyze");
        // We override the real restTemplate created in the constructor with our mock
        ReflectionTestUtils.setField(mlService, "restTemplate", restTemplate);
    }

    @Test
    public void testAnalyzeGraph_Success() {
        IntakeRequest request = new IntakeRequest();
        String expectedResponse = "{\"status\":\"success\"}";
        
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenReturn(new ResponseEntity<>(expectedResponse, HttpStatus.OK));

        String response = mlService.analyzeGraph(request);
        assertEquals(expectedResponse, response);
    }

    @Test
    public void testAnalyzeGraph_Non2xxStatus_ThrowsException() {
        IntakeRequest request = new IntakeRequest();
        
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenReturn(new ResponseEntity<>("Error", HttpStatus.INTERNAL_SERVER_ERROR));

        RuntimeException exception = assertThrows(RuntimeException.class, () -> mlService.analyzeGraph(request));
        assertTrue(exception.getMessage().contains("ML Service returned non-2xx status"));
    }

    @Test
    public void testAnalyzeGraph_ConnectionError_ThrowsException() {
        IntakeRequest request = new IntakeRequest();
        
        when(restTemplate.postForEntity(anyString(), any(HttpEntity.class), eq(String.class)))
                .thenThrow(new RuntimeException("Connection refused"));

        RuntimeException exception = assertThrows(RuntimeException.class, () -> mlService.analyzeGraph(request));
        assertTrue(exception.getMessage().contains("Failed to connect to ML service"));
    }
}
