package com.mulenet.api.controller;

import com.mulenet.api.service.NotificationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/stream")
@CrossOrigin(origins = "*")
public class StreamController {

    @Autowired
    private NotificationService notificationService;

    // SSE endpoint for the StreamMonitor live feed
    @GetMapping(value = "/subscribe", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @PreAuthorize("hasAnyRole('INVESTIGATOR', 'SUPERVISOR', 'FRAUD_ADMIN', 'COMPLIANCE_OFFICER')")
    public SseEmitter subscribeStream() {
        return notificationService.subscribeStream();
    }
}
