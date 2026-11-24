package com.mulenet.api.platform;

import java.io.IOException;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

@RestController
@Profile("platform")
public class DecisionStream {
    private final JdbcTemplate db;
    private final ServiceTokens tokens;
    private final Map<String, Stream> streams = new ConcurrentHashMap<>();
    private static class Stream {
        String tenant;
        String subject;
        SseEmitter emitter;
        long cursor;
        long expiry;
    }
    public DecisionStream(JdbcTemplate db, ServiceTokens tokens) { this.db = db; this.tokens = tokens; }

    @GetMapping("/api/health")
    public Map<String, String> alive() { return Map.of("status", "alive"); }

    @PostMapping("/api/v1/stream-token")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN','AUDITOR')")
    public Map<String, Object> token(Authentication auth) {
        var jwt = ((JwtAuthenticationToken) auth).getToken();
        Instant expiry = Instant.now().plusSeconds(60);
        if (jwt.getExpiresAt().isBefore(expiry)) expiry = jwt.getExpiresAt();
        List<String> roles = auth.getAuthorities().stream().map(a -> a.getAuthority().replace("ROLE_", "")).toList();
        return Map.of("access_token", tokens.stream(PlatformController.tenant(auth), auth.getName(), roles, expiry), "expires_at", expiry.getEpochSecond());
    }

    @GetMapping(value = "/api/v1/events", produces = "text/event-stream")
    @PreAuthorize("hasAnyRole('ANALYST','SUPERVISOR','ADMIN','AUDITOR')")
    public SseEmitter connect(Authentication auth, @RequestHeader(value = "Last-Event-ID", required = false) Long lastEventId) throws IOException {
        String tenant = PlatformController.tenant(auth);
        if (streams.size() >= 128 || streams.values().stream().filter(s -> s.tenant.equals(tenant) && s.subject.equals(auth.getName())).count() >= 2)
            throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "Stream connection limit");
        Stream stream = new Stream();
        stream.tenant = tenant;
        stream.subject = auth.getName();
        long seconds = Math.min(60, ((JwtAuthenticationToken) auth).getToken().getExpiresAt().getEpochSecond() - Instant.now().getEpochSecond());
        if (seconds <= 0) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Stream token expired");
        stream.expiry = Instant.now().getEpochSecond() + seconds;
        stream.emitter = new SseEmitter(seconds * 1000);
        Long latest = db.queryForObject("SELECT MAX(id) FROM platform_outbox WHERE tenant=? AND kind IN ('decision','case')", Long.class, tenant);
        stream.cursor = lastEventId == null ? (latest == null ? 0 : latest) : Math.max(0, lastEventId);
        String id = UUID.randomUUID().toString();
        stream.emitter.onCompletion(() -> streams.remove(id));
        stream.emitter.onTimeout(() -> { streams.remove(id); stream.emitter.complete(); });
        stream.emitter.onError(e -> streams.remove(id));
        streams.put(id, stream);
        stream.emitter.send(SseEmitter.event().name("ready").id(Long.toString(stream.cursor)).data(Map.of("tenant", tenant)));
        return stream.emitter;
    }

    @Scheduled(fixedDelay = 250)
    public void dispatch() {
        for (Map.Entry<String, Stream> entry : streams.entrySet()) {
            Stream stream = entry.getValue();
            try {
                if (Instant.now().getEpochSecond() >= stream.expiry) { stream.emitter.complete(); streams.remove(entry.getKey()); continue; }
                for (Map<String, Object> row : db.queryForList("SELECT id,kind,payload FROM platform_outbox WHERE tenant=? AND id>? AND kind IN ('decision','case') ORDER BY id LIMIT 100", stream.tenant, stream.cursor)) {
                    stream.emitter.send(SseEmitter.event().name((String) row.get("kind")).id(row.get("id").toString()).data((String) row.get("payload")));
                    stream.cursor = ((Number) row.get("id")).longValue();
                }
            } catch (IOException | IllegalStateException failure) { streams.remove(entry.getKey()); stream.emitter.complete(); }
        }
    }
}
