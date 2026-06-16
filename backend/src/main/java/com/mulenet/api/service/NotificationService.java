package com.mulenet.api.service;

import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

@Service
public class NotificationService {

    private final List<SseEmitter> emitters = Collections.synchronizedList(new ArrayList<>());

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
}
