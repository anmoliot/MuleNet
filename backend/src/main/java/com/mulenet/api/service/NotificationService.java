package com.mulenet.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.mulenet.api.model.Case;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

@Service
public class NotificationService {

    // Alert emitters — used by the bell icon / notifications panel
    private final List<SseEmitter> emitters = Collections.synchronizedList(new ArrayList<>());

    // Stream emitters — used exclusively by StreamMonitor feed
    private final List<SseEmitter> streamEmitters = Collections.synchronizedList(new ArrayList<>());

    private final ObjectMapper objectMapper = new ObjectMapper();

    // -----------------------------------------------------------------------
    // Alert channel (existing behaviour — unchanged)
    // -----------------------------------------------------------------------

    public SseEmitter subscribe() {
        SseEmitter emitter = new SseEmitter(180_000L); // 3-minute timeout
        emitters.add(emitter);

        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> emitters.remove(emitter));
        emitter.onError((e) -> emitters.remove(emitter));

        // Send initial connect message
        try {
            emitter.send(SseEmitter.event()
                    .name("connect")
                    .data("Connected to MuleNet notification channel"));
        } catch (IOException e) {
            emitters.remove(emitter);
        }

        return emitter;
    }

    public void broadcast(String title, String message, String severity) {
        List<SseEmitter> deadEmitters = new ArrayList<>();
        Map<String, String> payload = new HashMap<>();
        payload.put("title", title);
        payload.put("message", message);
        payload.put("severity", severity);
        payload.put("timestamp", java.time.LocalDateTime.now().toString());

        synchronized (emitters) {
            for (SseEmitter emitter : emitters) {
                try {
                    emitter.send(SseEmitter.event()
                            .name("alert")
                            .data(payload));
                } catch (Exception e) {
                    deadEmitters.add(emitter);
                }
            }
            emitters.removeAll(deadEmitters);
        }
    }

    // -----------------------------------------------------------------------
    // Stream channel — dedicated pool for StreamMonitor Live Feed
    // -----------------------------------------------------------------------

    /**
     * Subscribe to the live Kafka→Pipeline stream feed.
     * Events are of type "stream_event" and contain full transaction +
     * PolicyEngine decision data.
     */
    public SseEmitter subscribeStream() {
        SseEmitter emitter = new SseEmitter(300_000L); // 5-minute timeout
        streamEmitters.add(emitter);

        emitter.onCompletion(() -> streamEmitters.remove(emitter));
        emitter.onTimeout(() -> streamEmitters.remove(emitter));
        emitter.onError((e) -> streamEmitters.remove(emitter));

        try {
            emitter.send(SseEmitter.event()
                    .name("stream_connect")
                    .data("Connected to MuleNet live Kafka stream"));
        } catch (IOException e) {
            streamEmitters.remove(emitter);
        }

        return emitter;
    }

    /**
     * Broadcast a processed Kafka transaction event to all stream subscribers.
     * Called by KafkaConsumerService after PolicyEngine produces a decision.
     *
     * @param txnMap    raw transaction fields from the Kafka message
     * @param fraudCase the persisted Case entity from PolicyEngine
     */
    public void broadcastStreamEvent(Map<String, Object> txnMap, Case fraudCase) {
        Map<String, Object> payload = new LinkedHashMap<>();

        // Transaction fields
        payload.put("utr",              txnMap.getOrDefault("utr", ""));
        payload.put("amount",           txnMap.getOrDefault("amount", 0));
        payload.put("timestamp",        txnMap.getOrDefault("timestamp", java.time.Instant.now().toString()));
        payload.put("sender_account",   txnMap.getOrDefault("sender_account", ""));
        payload.put("receiver_account", txnMap.getOrDefault("receiver_account", ""));
        payload.put("device_id",        txnMap.getOrDefault("device_id", ""));

        // PolicyEngine decision fields
        payload.put("case_id",          fraudCase.getCaseId());
        payload.put("risk_score",       fraudCase.getRiskScore());
        payload.put("severity",         fraudCase.getSeverityLevel());

        // Derive policy_decision from risk score using the same thresholds as PolicyEngine
        double risk = fraudCase.getRiskScore();
        String policyDecision;
        if (risk >= 70.0)      policyDecision = "FREEZE_IMMEDIATE";
        else if (risk >= 60.0) policyDecision = "ESCALATE";
        else if (risk >= 50.0) policyDecision = "SOFT_HOLD";
        else if (risk >= 25.0) policyDecision = "STEP_UP_MONITOR";
        else                   policyDecision = "MONITOR";
        payload.put("policy_decision", policyDecision);

        // Top contributing features (static heuristic — replace with SHAP later)
        List<String> topFeatures = new ArrayList<>();
        if (risk >= 60.0) topFeatures.add("pass_through_rate");
        if (risk >= 50.0) topFeatures.add("fan_out_ratio");
        if (risk >= 40.0) topFeatures.add("counterparty_entropy");
        if (topFeatures.isEmpty()) topFeatures.add("low_velocity");
        payload.put("top_features", topFeatures);

        // Serialize and broadcast
        String json;
        try {
            json = objectMapper.writeValueAsString(payload);
        } catch (Exception e) {
            json = "{}";
        }

        List<SseEmitter> deadEmitters = new ArrayList<>();
        final String finalJson = json;
        synchronized (streamEmitters) {
            for (SseEmitter emitter : streamEmitters) {
                try {
                    emitter.send(finalJson);
                } catch (Exception e) {
                    deadEmitters.add(emitter);
                }
            }
            streamEmitters.removeAll(deadEmitters);
        }
    }

    /** Returns count of active stream subscribers (for health/debug). */
    public int streamSubscriberCount() {
        return streamEmitters.size();
    }
}
