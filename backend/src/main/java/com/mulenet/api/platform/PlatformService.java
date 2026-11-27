package com.mulenet.api.platform;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Instant;
import java.util.*;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
@Profile("platform")
public class PlatformService {
    private final JdbcTemplate db;
    private final ObjectMapper json;
    private final PrivacyCodec privacy;
    private final ServiceTokens tokens;
    private final CandidateClient ml;
    private final MeterRegistry meters;
    private final jakarta.validation.Validator validator;

    public PlatformService(JdbcTemplate db, ObjectMapper json, PrivacyCodec privacy,
                           ServiceTokens tokens, CandidateClient ml, MeterRegistry meters, jakarta.validation.Validator validator) {
        this.db = db;
        this.json = json.copy().configure(com.fasterxml.jackson.databind.SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
        // Persisted audit JSON can contain encrypted text larger than an input scalar.
        this.json.getFactory().setStreamReadConstraints(com.fasterxml.jackson.core.StreamReadConstraints.builder().maxNestingDepth(64).maxStringLength(2_000_000).maxNumberLength(40).build());
        this.privacy = privacy;
        this.tokens = tokens;
        this.ml = ml;
        this.meters = meters;
        this.validator = validator;
    }

    String encode(Object value) {
        try { return json.writeValueAsString(value); }
        catch (Exception e) { throw new IllegalArgumentException("Invalid platform JSON", e); }
    }
    JsonNode decode(String value) {
        try { return json.readTree(value); }
        catch (Exception e) { throw new IllegalStateException("Corrupt persisted JSON", e); }
    }
    private long now() { return Instant.now().getEpochSecond(); }

    private void lockTenant(String tenant) {
        db.update("INSERT INTO platform_tenants(tenant) VALUES (?) ON CONFLICT DO NOTHING", tenant);
        db.queryForObject("SELECT watermark FROM platform_tenants WHERE tenant=? FOR UPDATE", Long.class, tenant);
        if (db.queryForObject("SELECT COUNT(*) FROM platform_policies WHERE tenant=?", Long.class, tenant) == 0) {
            db.update("INSERT INTO platform_policies(tenant,version,config,actor,created_at) VALUES (?,1,?,'bootstrap',?)", tenant, encode(ReviewPolicy.initial()), now());
            audit(tenant, "bootstrap", "POLICY_INITIALIZED", Map.of("version", 1));
        }
    }

    private void audit(String tenant, String actor, String action, Object detail) {
        Map<String, Object> head = db.queryForMap("SELECT audit_sequence,audit_head FROM platform_tenants WHERE tenant=? FOR UPDATE", tenant);
        long sequence = ((Number) head.get("audit_sequence")).longValue() + 1;
        String previous = (String) head.get("audit_head");
        String payload = encode(Map.of("sequence", sequence, "tenant", tenant, "actor", actor, "action", action, "detail", detail, "time", now()));
        String hash = PrivacyCodec.hash(previous + "\n" + payload);
        db.update("INSERT INTO platform_audit(tenant,sequence,previous_hash,entry_hash,payload) VALUES (?,?,?,?,?)", tenant, sequence, previous, hash, payload);
        db.update("UPDATE platform_tenants SET audit_sequence=?,audit_head=? WHERE tenant=?", sequence, hash, tenant);
    }

    private void outbox(String tenant, String id, String key, String kind, String payload) {
        String hash = PrivacyCodec.hash(payload);
        int inserted = db.update("INSERT INTO platform_outbox(event_id,tenant,partition_key,kind,payload,payload_hash,created_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
            id, tenant, key, kind, payload, hash, now());
        if (inserted == 0 && !hash.equals(db.queryForObject("SELECT payload_hash FROM platform_outbox WHERE event_id=? AND tenant=?", String.class, id, tenant)))
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Conflicting idempotency key");
    }

    @Transactional
    public List<String> enqueue(String tenant, String actor, List<Payment> payments) {
        lockTenant(tenant);
        List<String> ids = new ArrayList<>();
        for (Payment payment : payments) {
            if (payment.ts() > now() + 300) throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "Future-dated event");
            String id = privacy.token(tenant, "transaction", payment.transactionId());
            ObjectNode event = json.createObjectNode();
            event.put("transaction_id", id).put("source", privacy.token(tenant, "account", payment.source()))
                .put("target", privacy.token(tenant, "account", payment.target())).put("ts", payment.ts())
                .put("amount", payment.amount()).put("currency", payment.currency()).put("kind", payment.kind());
            if (payment.deviceId() != null) event.put("device_id", privacy.token(tenant, "device", payment.deviceId()));
            if (payment.ipAddress() != null) event.put("ip_address", privacy.token(tenant, "ip", payment.ipAddress()));
            String body = encode(event);
            String eventId = PrivacyCodec.hash(tenant + ":ingest:" + id);
            // Compare deterministic bodies, not randomized signatures/encryption.
            List<String> existing = db.queryForList("SELECT payload FROM platform_outbox WHERE event_id=? AND tenant=?", String.class, eventId, tenant);
            if (!existing.isEmpty()) {
                String oldHash = db.queryForObject("SELECT payload_hash FROM platform_vault WHERE tenant=? AND transaction_id=?", String.class, tenant, id);
                if (!PrivacyCodec.hash(body).equals(oldHash)) throw new ResponseStatusException(HttpStatus.CONFLICT, "Conflicting transaction ID");
            } else {
                outbox(tenant, eventId, tenant + ":" + event.path("source").asText(), "ingestion", tokens.ingestion(tenant, eventId, body));
                db.update("INSERT INTO platform_vault(tenant,transaction_id,ciphertext,payload_hash,created_at) VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING", tenant, id, privacy.encrypt(tenant, encode(payment)), PrivacyCodec.hash(body), now());
                audit(tenant, actor, "INGESTION_ACCEPTED", Map.of("transaction_id", id, "payload_hash", PrivacyCodec.hash(body)));
            }
            ids.add(id);
        }
        return ids;
    }

    @Transactional
    public void process(String tenant, JsonNode event, String correlation) {
        lockTenant(tenant);
        Payment normalized;
        try { normalized = json.treeToValue(event, Payment.class); }
        catch (Exception invalid) { throw new IllegalArgumentException("Signed event schema rejected", invalid); }
        if (!validator.validate(normalized).isEmpty()) throw new IllegalArgumentException("Signed event validation failed");
        String id = event.path("transaction_id").asText();
        long ts = event.path("ts").asLong(-1);
        String body = encode(event);
        String hash = PrivacyCodec.hash(body);
        List<String> existing = db.queryForList("SELECT payload_hash FROM platform_ledger WHERE tenant=? AND transaction_id=?", String.class, tenant, id);
        if (!existing.isEmpty()) {
            if (!hash.equals(existing.get(0))) throw new IllegalArgumentException("Conflicting duplicate delivery");
            meters.counter("mulenet.ingestion.duplicates").increment();
            return;
        }
        long watermark = db.queryForObject("SELECT watermark FROM platform_tenants WHERE tenant=?", Long.class, tenant);
        if (ts < watermark) throw new IllegalArgumentException("Late event requires explicit historical replay, not an altered online snapshot");
        if (!id.matches("[a-f0-9]{64}") || !event.path("source").asText().matches("[a-f0-9]{64}") || !event.path("target").asText().matches("[a-f0-9]{64}") ||
            !event.path("amount").isNumber() || !Double.isFinite(event.path("amount").asDouble()) || event.path("amount").asDouble() <= 0 ||
            !event.path("currency").asText().equals("INR") || ts < 0 || ts > now() + 300)
            throw new IllegalArgumentException("Invalid signed event contract");
        db.update("INSERT INTO platform_ledger(tenant,transaction_id,source_account,target_account,event_time,payload_hash,payload) VALUES (?,?,?,?,?,?,?)",
            tenant, id, event.path("source").asText(), event.path("target").asText(), ts, hash, body);
        db.update("UPDATE platform_tenants SET watermark=? WHERE tenant=?", ts, tenant);
        List<JsonNode> context = db.query("SELECT payload FROM platform_ledger WHERE tenant=? AND event_time<=? ORDER BY event_time,transaction_id LIMIT 8193", (rs, n) -> decode(rs.getString(1)), tenant, ts);
        Map<String, Object> policyRow = policy(tenant);
        ReviewPolicy policy = json.convertValue(decode((String) policyRow.get("config")), ReviewPolicy.class);
        int policyVersion = ((Number) policyRow.get("version")).intValue();
        Set<String> accounts = new TreeSet<>(List.of(event.path("source").asText(), event.path("target").asText()));
        for (String account : accounts) {
            ObjectNode result;
            try {
                if (context.size() > 8192) throw new IllegalStateException("Complete graph context exceeds reference service capacity");
                long completeFrom = context.stream().mapToLong(e -> e.path("ts").asLong()).min().orElse(ts);
                result = (ObjectNode) ml.score(tenant, account, ts, correlation, completeFrom, context);
            } catch (RuntimeException failure) {
                String failureCode = failure instanceof org.springframework.web.client.HttpStatusCodeException statusError ? "ML_HTTP_" + statusError.getStatusCode().value() :
                    failure instanceof io.github.resilience4j.circuitbreaker.CallNotPermittedException ? "ML_CIRCUIT_OPEN" :
                    failure instanceof org.springframework.web.client.ResourceAccessException ? "ML_TRANSPORT_UNAVAILABLE" : "ML_CONTRACT_OR_CONTEXT_FAILURE";
                result = json.createObjectNode();
                result.putNull("probability").put("model_version", "unavailable").putNull("feature_schema_hash")
                    .put("model", "rules_only").put("degraded", true).put("degradation_reason", failureCode)
                    .put("data_provenance", "synthetic");
                result.set("score_components", json.valueToTree(Map.of("structuring_rule", event.path("amount").asDouble() >= 47500 && event.path("amount").asDouble() < 50000)));
                result.set("reason_codes", json.valueToTree(List.of(Map.of("code", "DEGRADED_REVIEW_REQUIRED"))));
                result.set("evidence", json.valueToTree(Map.of("edges", List.of(event))));
                meters.counter("mulenet.decisions.degraded").increment();
                meters.counter("mulenet.decisions.failure", "reason", failureCode).increment();
            }
            double threshold = policy.threshold(result.path("validation_threshold").asDouble(1));
            boolean hold = result.path("degraded").asBoolean() || result.path("probability").asDouble(-1) >= threshold;
            String decisionId = PrivacyCodec.hash(tenant + ":" + id + ":" + account);
            String status = hold ? "SOFT_HOLD" : "MONITOR";
            Long expiry = hold ? now() + policy.maxHoldSeconds() : null;
            result.put("decision_id", decisionId).put("account_id", account).put("transaction_id", id)
                .put("as_of", ts).put("correlation_id", correlation).put("thresholds_version", policyVersion)
                .put("policy_threshold", threshold).put("policy_action", status).put("external_intervention", false);
            result.set("cost_assumptions", json.valueToTree(policy));
            db.update("INSERT INTO platform_decisions(decision_id,tenant,transaction_id,account_id,as_of,result,status,expires_at,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                decisionId, tenant, id, account, ts, encode(result), status, expiry, now());
            audit(tenant, "decision-worker", "DECISION_CREATED", result);
            outbox(tenant, decisionId, tenant + ":" + account, "decision", encode(result));
            meters.counter("mulenet.decisions", "model", result.path("model").asText()).increment();
        }
    }

    public Map<String, Object> policy(String tenant) {
        List<Map<String, Object>> rows = db.queryForList("SELECT version,config FROM platform_policies WHERE tenant=? ORDER BY version DESC LIMIT 1", tenant);
        return rows.isEmpty() ? Map.of("version", 0, "config", encode(ReviewPolicy.initial())) : rows.get(0);
    }

    @Transactional
    public Map<String, Object> changePolicy(String tenant, String actor, int expectedVersion, ReviewPolicy next, String rationale) {
        lockTenant(tenant);
        Map<String, Object> before = policy(tenant);
        int current = ((Number) before.get("version")).intValue();
        if (current != expectedVersion) throw new ResponseStatusException(HttpStatus.CONFLICT, "Policy changed; reload before editing");
        db.update("INSERT INTO platform_policies(tenant,version,config,actor,created_at) VALUES (?,?,?,?,?)", tenant, current + 1, encode(next), actor, now());
        audit(tenant, actor, "POLICY_CHANGED", Map.of("before", before, "after", next, "version", current + 1, "rationale_ciphertext", privacy.encrypt(tenant, rationale)));
        return policy(tenant);
    }

    public List<Map<String, Object>> decisions(String tenant) {
        return db.queryForList("SELECT decision_id,account_id,as_of,result,status,assignee,version,expires_at,created_at FROM platform_decisions WHERE tenant=? ORDER BY created_at DESC,decision_id LIMIT 200", tenant);
    }

    public Map<String, Object> decision(String tenant, String id) {
        List<Map<String, Object>> rows = db.queryForList("SELECT * FROM platform_decisions WHERE tenant=? AND decision_id=?", tenant, id);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Decision not found");
        return rows.get(0);
    }

    @Transactional
    public Map<String, Object> act(String tenant, String actor, String id, int expectedVersion, String action, String rationale, String assignee) {
        lockTenant(tenant);
        Map<String, Object> before = decision(tenant, id);
        int version = ((Number) before.get("version")).intValue();
        if (version != expectedVersion) throw new ResponseStatusException(HttpStatus.CONFLICT, "Case changed; reload before acting");
        String status = (String) before.get("status");
        switch (action) {
            case "ASSIGN" -> { if (assignee == null || assignee.isBlank()) throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "Assignee required"); }
            case "NOTE" -> { }
            case "APPEAL" -> status = "UNDER_REVIEW";
            case "APPROVE" -> {
                if (!Set.of("SOFT_HOLD", "UNDER_REVIEW").contains(status) || before.get("expires_at") == null || ((Number) before.get("expires_at")).longValue() <= now())
                    throw new ResponseStatusException(HttpStatus.CONFLICT, "No active hold to approve");
                status = "HOLD_APPROVED";
            }
            case "RELEASE" -> status = "RELEASED";
            case "REJECT" -> status = "REJECTED";
            default -> throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "Unknown case action");
        }
        db.update("UPDATE platform_decisions SET status=?,assignee=?,version=version+1 WHERE tenant=? AND decision_id=?", status,
            action.equals("ASSIGN") ? assignee : before.get("assignee"), tenant, id);
        Map<String, Object> after = decision(tenant, id);
        audit(tenant, actor, "CASE_" + action, Map.of("before", before, "after", after, "rationale_ciphertext", privacy.encrypt(tenant, rationale)));
        outbox(tenant, UUID.randomUUID().toString(), tenant + ":" + before.get("account_id"), "case", encode(after));
        return after;
    }

    @Transactional
    public void releaseExpired() {
        List<String> tenants = db.queryForList("SELECT DISTINCT tenant FROM platform_decisions WHERE expires_at<=? AND status IN ('SOFT_HOLD','HOLD_APPROVED','UNDER_REVIEW')", String.class, now());
        for (String tenant : tenants) {
            lockTenant(tenant);
            for (Map<String, Object> row : db.queryForList("SELECT decision_id,version FROM platform_decisions WHERE tenant=? AND expires_at<=? AND status IN ('SOFT_HOLD','HOLD_APPROVED','UNDER_REVIEW')", tenant, now())) {
                act(tenant, "hold-expiry", (String) row.get("decision_id"), ((Number) row.get("version")).intValue(), "RELEASE", "Maximum hold duration elapsed", null);
            }
        }
    }

    public List<Map<String, Object>> auditEntries(String tenant) {
        return auditEntries(tenant, 0, 100);
    }
    public List<Map<String, Object>> auditEntries(String tenant, long after, int limit) {
        return db.queryForList("SELECT sequence,previous_hash,entry_hash,payload FROM platform_audit WHERE tenant=? AND sequence>? ORDER BY sequence LIMIT ?", tenant, after, limit);
    }
    public String circuitState() { return ml.circuitState(); }
    public JsonNode drift(String tenant) { return ml.drift(tenant); }

    public List<Map<String, Object>> notes(String tenant, String id) {
        decision(tenant, id);
        List<Map<String, Object>> notes = new ArrayList<>();
        for (Map<String, Object> row : db.queryForList("SELECT payload FROM platform_audit WHERE tenant=? AND payload::jsonb->'detail'->'before'->>'decision_id'=? AND payload::jsonb->>'action' LIKE 'CASE_%' ORDER BY sequence DESC LIMIT 100", tenant, id)) {
            JsonNode payload = decode((String) row.get("payload"));
            if (payload.path("action").asText().startsWith("CASE_") && payload.path("detail").path("before").path("decision_id").asText().equals(id)) {
                notes.add(Map.of("actor", payload.path("actor").asText(), "time", payload.path("time").asLong(),
                    "action", payload.path("action").asText(), "rationale", privacy.decrypt(tenant, payload.path("detail").path("rationale_ciphertext").asText())));
            }
        }
        return notes;
    }

    @Transactional
    public void feedback(String tenant, String actor, String id, boolean fraudulent, String evidence, String role) {
        lockTenant(tenant);
        Map<String, Object> decision = decision(tenant, id);
        if (!Set.of("RELEASED", "REJECTED").contains((String) decision.get("status")))
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Resolve the case before independent adjudication");
        long recent = db.queryForObject("SELECT COUNT(*) FROM platform_feedback WHERE tenant=? AND reviewer=? AND created_at>?", Long.class, tenant, actor, now() - 86400);
        if (recent >= 20) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "Adjudication quality-review limit reached");
        db.update("INSERT INTO platform_feedback(tenant,decision_id,reviewer,reviewer_role,fraudulent,evidence,created_at) VALUES (?,?,?,?,?,?,?)",
            tenant, id, actor, role, fraudulent, privacy.encrypt(tenant, evidence), now());
        audit(tenant, actor, "LABEL_ADJUDICATED", Map.of("decision_id", id, "fraudulent", fraudulent, "evidence_ciphertext", privacy.encrypt(tenant, evidence)));
    }

    public List<Map<String, Object>> feedbackExport(String tenant) {
        return db.queryForList("SELECT f.decision_id,f.reviewer,f.reviewer_role,f.fraudulent,f.created_at,d.account_id,d.as_of FROM platform_feedback f JOIN platform_decisions d ON f.decision_id=d.decision_id AND f.tenant=d.tenant WHERE f.tenant=? ORDER BY f.decision_id,f.reviewer", tenant);
    }

    @Transactional
    public void replay(String tenant, String actor, String transactionId, String rationale) {
        lockTenant(tenant);
        // Only originally accepted, tenant-bound ledger inputs are eligible for replay.
        String eventId = PrivacyCodec.hash(tenant + ":ingest:" + transactionId);
        String original = db.queryForObject("SELECT payload FROM platform_outbox WHERE tenant=? AND event_id=? AND kind='ingestion'", String.class, tenant, eventId);
        io.jsonwebtoken.Claims claims;
        try { claims = tokens.verifyIngestion(original); }
        catch (io.jsonwebtoken.ExpiredJwtException expired) { claims = expired.getClaims(); }
        JsonNode body = decode(claims.get("body", String.class));
        String replayId = UUID.randomUUID().toString();
        outbox(tenant, replayId, tenant + ":" + body.path("source").asText(), "ingestion", tokens.ingestion(tenant, replayId, encode(body)));
        audit(tenant, actor, "DLQ_REPLAY_REQUESTED", Map.of("transaction_id", transactionId, "rationale_ciphertext", privacy.encrypt(tenant, rationale)));
    }
}
