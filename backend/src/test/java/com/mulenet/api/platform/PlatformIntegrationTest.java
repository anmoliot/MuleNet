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
class PlatformIntegrationTest {
    private static final Network NETWORK = Network.newNetwork();
    private static final String SERVICE_SECRET = UUID.randomUUID().toString() + UUID.randomUUID();
    private static final String STREAM_SECRET = UUID.randomUUID().toString() + UUID.randomUUID();
    private static final String INGESTION_SECRET = UUID.randomUUID().toString() + UUID.randomUUID();
    private static final String KEY = Base64.getEncoder().encodeToString(java.security.SecureRandom.getSeed(32));
    private static final String RUNTIME_PASSWORD = UUID.randomUUID().toString();
    private static final Map<String, String> PASSWORDS = Map.of("analyst", UUID.randomUUID().toString(), "supervisor", UUID.randomUUID().toString(), "admin", UUID.randomUUID().toString(), "auditor", UUID.randomUUID().toString());
    private static final String INIT_SQL = "CREATE ROLE mulenet_runtime LOGIN PASSWORD '" + RUNTIME_PASSWORD + "'; GRANT USAGE ON SCHEMA public TO mulenet_runtime; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO mulenet_runtime; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO mulenet_runtime;";
    @Container static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:17.7-alpine")
        .withDatabaseName("mulenet").withUsername("migration").withPassword(UUID.randomUUID().toString())
        .withCopyToContainer(Transferable.of(INIT_SQL), "/docker-entrypoint-initdb.d/10-runtime.sql").withNetwork(NETWORK);
    @Container static KafkaContainer kafka = new KafkaContainer(DockerImageName.parse("apache/kafka:4.1.1")).withNetwork(NETWORK);
    @Container static GenericContainer<?> redis = new GenericContainer<>("redis:7.4.7-alpine").withExposedPorts(6379).withNetwork(NETWORK).withNetworkAliases("redis");
    @Container static GenericContainer<?> ml = new GenericContainer<>(System.getenv().getOrDefault("MULENET_ML_TEST_IMAGE", "mulenet/ml:local"))
        .withNetwork(NETWORK).dependsOn(redis).withExposedPorts(8000)
        .withFileSystemBind(Path.of("../artifacts/demo-temporal-v3").toAbsolutePath().normalize().toString(), "/models", BindMode.READ_ONLY)
        .withEnv("MULENET_MODEL_DIR", "/models").withEnv("MULENET_ALLOW_SYNTHETIC", "true")
        .withEnv("MULENET_SERVICE_SECRET", SERVICE_SECRET).withEnv("MULENET_REDIS_URL", "redis://redis:6379/0")
        .waitingFor(org.testcontainers.containers.wait.strategy.Wait.forHttp("/health").forPort(8000)).withStartupTimeout(Duration.ofMinutes(2));

    @DynamicPropertySource static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "mulenet_runtime");
        registry.add("spring.datasource.password", () -> RUNTIME_PASSWORD);
        registry.add("spring.datasource.driverClassName", () -> "org.postgresql.Driver");
        registry.add("spring.jpa.properties.hibernate.dialect", () -> "org.hibernate.dialect.PostgreSQLDialect");
        registry.add("spring.jpa.hibernate.ddl-auto", () -> "validate");
        registry.add("spring.flyway.enabled", () -> true);
        registry.add("spring.flyway.user", postgres::getUsername);
        registry.add("spring.flyway.password", postgres::getPassword);
        registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
        registry.add("mulenet.token-key", () -> KEY);
        registry.add("mulenet.encryption-key", () -> KEY);
        registry.add("mulenet.service-secret", () -> SERVICE_SECRET);
        registry.add("mulenet.stream-secret", () -> STREAM_SECRET);
        registry.add("mulenet.ingestion-secret", () -> INGESTION_SECRET);
        registry.add("mulenet.ml-url", () -> "http://" + ml.getHost() + ":" + ml.getMappedPort(8000));
        registry.add("mulenet.demo-jwt-secret", () -> KEY);
        PASSWORDS.forEach((role, password) -> registry.add("mulenet.demo-passwords." + role, () -> password));
    }

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
        String previous = "GENESIS";
        for (Map<String, Object> row : platform.auditEntries("demo")) {
            assertEquals(previous, row.get("previous_hash"));
            assertEquals(PrivacyCodec.hash(previous + "\n" + row.get("payload")), row.get("entry_hash"));
            previous = (String) row.get("entry_hash");
        }
    }
}
