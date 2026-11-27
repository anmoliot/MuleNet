package com.mulenet.api.platform;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.*;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.*;
import org.testcontainers.junit.jupiter.*;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.images.builder.Transferable;
import org.testcontainers.kafka.KafkaContainer;
import org.testcontainers.utility.*;
import static org.awaitility.Awaitility.await;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles({"platform", "demo"})
@Testcontainers
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class PlatformIntegrationTest extends PlatformTestStack {

    @Autowired MockMvc http;
    @Autowired ObjectMapper json;
    @Autowired JdbcTemplate db;
    @Autowired PlatformService platform;
    @Autowired PrivacyCodec privacy;
    @Autowired ServiceTokens tokens;
    @Autowired @org.springframework.beans.factory.annotation.Qualifier("platformKafka") org.springframework.kafka.core.KafkaTemplate<String, String> producer;

    private String login(String role) throws Exception {
        String response = http.perform(post("/api/v1/auth/login").contentType("application/json")
            .content(json.writeValueAsString(Map.of("username", role, "password", PASSWORDS.get(role)))))
            .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        return "Bearer " + json.readTree(response).path("access_token").asText();
    }

    @Test void initialPolicyVersionAndVerifiedIdentity() throws Exception {
        http.perform(get("/api/v1/auth/session")).andExpect(status().isUnauthorized());
        String admin = login("admin");
        http.perform(get("/api/v1/auth/session").header("Authorization", admin))
            .andExpect(status().isOk()).andExpect(jsonPath("$.tenant").value("demo"))
            .andExpect(jsonPath("$.roles[0]").value("ADMIN")).andExpect(jsonPath("$.demo_mode").value(true));
        String policy = json.writeValueAsString(Map.of("expectedVersion", 0,
            "config", ReviewPolicy.initial(), "rationale", "Preserve initial research policy with an audited first version"));
        http.perform(put("/api/v1/policy").header("Authorization", login("analyst"))
            .contentType("application/json").content(policy)).andExpect(status().isForbidden());
        admin = "Bearer " + io.jsonwebtoken.Jwts.builder()
            .setIssuer("mulenet-demo").setAudience("mulenet-api").setSubject("initial-policy-admin")
            .setIssuedAt(new Date()).setExpiration(Date.from(Instant.now().plusSeconds(60)))
            .claim("tenant", "initial-policy-test").claim("roles", List.of("ADMIN"))
            .signWith(io.jsonwebtoken.security.Keys.hmacShaKeyFor(Base64.getDecoder().decode(KEY)), io.jsonwebtoken.SignatureAlgorithm.HS256).compact();
        http.perform(put("/api/v1/policy").header("Authorization", admin)
            .contentType("application/json").content(policy)).andExpect(status().isOk()).andExpect(jsonPath("$.version").value(1));
        http.perform(put("/api/v1/policy").header("Authorization", admin)
            .contentType("application/json").content(policy)).andExpect(status().isConflict());
    }

    @Test void realStackReplayIdempotencyDlqDegradationAndReview() throws Exception {
        String admin = login("admin");
        String analyst = login("analyst");
        http.perform(post("/api/demo/seed")).andExpect(status().isUnauthorized());
        http.perform(post("/api/demo/seed").header("Authorization", analyst)).andExpect(status().isForbidden());
        http.perform(get("/api/v1/events")).andExpect(status().isUnauthorized());
        http.perform(get("/api/v1/events").header("Authorization", admin)).andExpect(status().isUnauthorized());
        http.perform(get("/api/v1/audit").header("Authorization", analyst)).andExpect(status().isForbidden());
        String body = json.writeValueAsString(Map.of("transactions", List.of(new Payment("integration-1", "raw-source", "raw-target", Instant.now().getEpochSecond(), 49000., "INR", "TRANSFER", "raw-device", null))));
        http.perform(post("/api/v1/transactions").contentType("application/json").header("Authorization", admin).content(body)).andExpect(status().isAccepted());
        await().atMost(Duration.ofSeconds(45)).until(() -> platform.decisions("demo").size() == 2);
        Map<String, Object> first = platform.decisions("demo").get(0);
        JsonNode result = json.readTree((String) first.get("result"));
        assertFalse(result.path("degraded").asBoolean(), result.toString());
        assertEquals("tabular_graph", result.path("model").asText());
        assertEquals(64, result.path("feature_schema_hash").asText().length());
        assertFalse(result.toString().contains("raw-source"));
        var metricsClient = java.net.http.HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
        var metricsUri = java.net.URI.create("http://" + ml.getHost() + ":" + ml.getMappedPort(8000) + "/metrics");
        assertEquals(401, metricsClient.send(java.net.http.HttpRequest.newBuilder(metricsUri).GET().build(), java.net.http.HttpResponse.BodyHandlers.ofString()).statusCode());
        assertEquals(403, metricsClient.send(java.net.http.HttpRequest.newBuilder(metricsUri).header("Authorization", "Bearer " + tokens.ml("demo")).GET().build(), java.net.http.HttpResponse.BodyHandlers.ofString()).statusCode());
        java.util.function.Function<String, String> metricsCredential = tenant -> io.jsonwebtoken.Jwts.builder()
            .setIssuer("mulenet-backend").setAudience("mulenet-ml").setSubject("backend")
            .setId(UUID.randomUUID().toString()).setIssuedAt(new Date()).setExpiration(Date.from(Instant.now().plusSeconds(30)))
            .claim("tenant", tenant).claim("scope", "metrics")
            .signWith(io.jsonwebtoken.security.Keys.hmacShaKeyFor(SERVICE_SECRET.getBytes(java.nio.charset.StandardCharsets.UTF_8)), io.jsonwebtoken.SignatureAlgorithm.HS256).compact();
        var driftMetrics = metricsClient.send(java.net.http.HttpRequest.newBuilder(metricsUri).header("Authorization", "Bearer " + metricsCredential.apply("demo")).GET().build(), java.net.http.HttpResponse.BodyHandlers.ofString());
        assertEquals(200, driftMetrics.statusCode());
        assertTrue(driftMetrics.body().contains("mulenet_ml_drift_samples{"));
        assertFalse(driftMetrics.body().contains("mulenet_ml_drift_psi{"));
        var isolatedMetrics = metricsClient.send(java.net.http.HttpRequest.newBuilder(metricsUri).header("Authorization", "Bearer " + metricsCredential.apply("isolated-metrics")).GET().build(), java.net.http.HttpResponse.BodyHandlers.ofString());
        assertEquals(200, isolatedMetrics.statusCode());
        assertFalse(isolatedMetrics.body().contains("mulenet_ml_drift_samples{"));
        String scoped = json.readTree(http.perform(post("/api/v1/stream-token").header("Authorization", admin))
            .andExpect(status().isOk()).andReturn().getResponse().getContentAsString()).path("access_token").asText();
        var stream = http.perform(get("/api/v1/events").header("Authorization", "Bearer " + scoped).header("Last-Event-ID", "0"))
            .andExpect(request().asyncStarted()).andReturn();
        String other = tokens.stream("other-tenant", "isolated-reader", List.of("ANALYST"), Instant.now().plusSeconds(30));
        var isolated = http.perform(get("/api/v1/events").header("Authorization", "Bearer " + other).header("Last-Event-ID", "0"))
            .andExpect(request().asyncStarted()).andReturn();
        await().atMost(Duration.ofSeconds(5)).until(() -> stream.getResponse().getContentAsString().contains("event:decision"));
        assertFalse(isolated.getResponse().getContentAsString().contains("event:decision"));
        stream.getRequest().getAsyncContext().complete();
        isolated.getRequest().getAsyncContext().complete();
        assertFalse(db.queryForObject("SELECT payload FROM platform_ledger LIMIT 1", String.class).contains("raw-device"));
        assertThrows(org.springframework.dao.DataAccessException.class, () -> db.update("UPDATE platform_audit SET payload='tampered'"));
        assertThrows(org.springframework.dao.DataAccessException.class, () -> db.update("UPDATE platform_policies SET config='{}'"));
        http.perform(post("/api/v1/transactions").contentType("application/json").header("Authorization", admin).content(body)).andExpect(status().isAccepted());
        String signed = db.queryForObject("SELECT payload FROM platform_outbox WHERE kind='ingestion' LIMIT 1", String.class);
        String source = privacy.token("demo", "account", "raw-source");
        producer.send("mulenet.transactions", "demo:" + source, signed).get();
        await().atMost(Duration.ofSeconds(20)).until(() -> db.queryForObject("SELECT COUNT(*) FROM platform_ledger", Long.class) == 1);
        assertEquals(2, platform.decisions("demo").size());
        http.perform(post("/api/v1/transactions").contentType("application/json").header("Authorization", admin).content(body.replace("49000.0", "48000.0"))).andExpect(status().isConflict());

        Properties consumerProperties = new Properties();
        consumerProperties.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, kafka.getBootstrapServers());
        consumerProperties.put(ConsumerConfig.GROUP_ID_CONFIG, UUID.randomUUID().toString());
        consumerProperties.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        try (KafkaConsumer<String, String> deadLetters = new KafkaConsumer<>(consumerProperties, new StringDeserializer(), new StringDeserializer())) {
            deadLetters.subscribe(List.of("mulenet.transactions.dlq"));
            producer.send("mulenet.transactions", "invalid-key", "forged.invalid.token").get();
            await().atMost(Duration.ofSeconds(30)).until(() -> {
                for (ConsumerRecord<String, String> record : deadLetters.poll(Duration.ofMillis(200))) {
                    JsonNode receipt = json.readTree(record.value());
                    assertTrue(receipt.has("encrypted_payload"));
                    assertFalse(record.value().contains("forged.invalid.token"));
                    return true;
                }
                return false;
            });
        }
        assertEquals(1L, db.queryForObject("SELECT COUNT(*) FROM platform_ledger", Long.class));
        ml.stop();
        String secondBody = json.writeValueAsString(Map.of("transactions", List.of(new Payment("integration-2", "raw-source", "raw-next", Instant.now().getEpochSecond(), 100., "INR", "TRANSFER", null, null))));
        http.perform(post("/api/v1/transactions").contentType("application/json").header("Authorization", admin).content(secondBody)).andExpect(status().isAccepted());
        await().atMost(Duration.ofSeconds(45)).until(() -> platform.decisions("demo").size() == 4);
        Map<String, Object> held = platform.decisions("demo").stream().filter(row -> row.get("status").equals("SOFT_HOLD")).findFirst().orElseThrow();
        JsonNode degraded = json.readTree((String) held.get("result"));
        assertTrue(degraded.path("degraded").asBoolean());
        assertTrue(degraded.get("probability").isNull());
        String id = (String) held.get("decision_id");
        String review = json.writeValueAsString(Map.of("expectedVersion", 1, "rationale", "Investigated evidence; release this simulated hold"));
        http.perform(post("/api/v1/decisions/" + id + "/actions/RELEASE").contentType("application/json").header("Authorization", analyst).content(review)).andExpect(status().isForbidden());
        http.perform(post("/api/v1/decisions/" + id + "/actions/RELEASE").contentType("application/json").header("Authorization", admin).content(review)).andExpect(status().isOk());
        assertEquals("RELEASED", platform.decision("demo", id).get("status"));
        assertTrue(platform.decisions("other-tenant").isEmpty());
        db.update("UPDATE platform_decisions SET expires_at=? WHERE status='SOFT_HOLD'", Instant.now().getEpochSecond() - 1);
        platform.releaseExpired();
        assertTrue(platform.decisions("demo").stream().noneMatch(row -> row.get("status").equals("SOFT_HOLD")));
        http.perform(get("/actuator/prometheus")).andExpect(status().isUnauthorized());
        http.perform(get("/actuator/prometheus").header("Authorization", analyst)).andExpect(status().isForbidden());
        String metrics = http.perform(get("/actuator/prometheus").header("Authorization", admin))
            .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        assertTrue(metrics.contains("mulenet_pipeline_stage_seconds_count"));
        assertTrue(metrics.contains("stage=\"score_http\""));
        assertTrue(metrics.contains("stage=\"kafka_process\""));
        assertFalse(metrics.contains("raw-source"));
        assertFalse(metrics.contains("raw-device"));
        String previous = "GENESIS";
        for (Map<String, Object> row : platform.auditEntries("demo")) {
            assertEquals(previous, row.get("previous_hash"));
            assertEquals(PrivacyCodec.hash(previous + "\n" + row.get("payload")), row.get("entry_hash"));
            previous = (String) row.get("entry_hash");
        }
    }
}
