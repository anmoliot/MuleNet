package com.mulenet.api.platform;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.*;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;
import org.testcontainers.junit.jupiter.Testcontainers;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles({"platform", "demo"})
@Testcontainers
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class PlatformLatencyTest extends PlatformTestStack {
    @LocalServerPort int port;
    @Autowired ObjectMapper json;
    @Autowired ServiceTokens tokens;
    @Autowired @Qualifier("platformKafka") KafkaTemplate<String, String> producer;
    private volatile String modelVersion;
    private volatile String schemaHash;
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

    private final class Pending {
        final long started = System.nanoTime();
        final Set<String> decisions = ConcurrentHashMap.newKeySet();
        final CompletableFuture<Double> milliseconds = new CompletableFuture<>();
    }

    private final class StreamReader implements AutoCloseable {
        final String tenant;
        final Map<String, Pending> pending = new ConcurrentHashMap<>();
        final CountDownLatch ready = new CountDownLatch(1);
        final AtomicBoolean closed = new AtomicBoolean();
        volatile InputStream input;
        volatile Throwable failure;
        String cursor = "0";
        final Thread thread;

        StreamReader(String tenant) throws Exception {
            this.tenant = tenant;
            thread = new Thread(this::read, "benchmark-sse-reader");
            thread.setDaemon(true);
            thread.start();
            if (!ready.await(15, TimeUnit.SECONDS) || failure != null) throw new IllegalStateException("Authenticated SSE did not become ready", failure);
        }

        void read() {
            try {
                while (!closed.get()) {
                    String bearer = tokens.stream(tenant, "benchmark", List.of("ANALYST"), Instant.now().plusSeconds(55));
                    var request = HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/api/v1/events"))
                        .header("Authorization", "Bearer " + bearer).header("Last-Event-ID", cursor).GET().build();
                    var response = client.send(request, HttpResponse.BodyHandlers.ofInputStream());
                    input = response.body();
                    if (response.statusCode() != 200) throw new IllegalStateException("SSE rejected: " + response.statusCode());
                    try (var lines = new BufferedReader(new InputStreamReader(input, StandardCharsets.UTF_8))) {
                        String line, kind = "", id = cursor;
                        StringBuilder data = new StringBuilder();
                        while (!closed.get() && (line = lines.readLine()) != null) {
                            if (line.startsWith("event:")) kind = line.substring(6).strip();
                            else if (line.startsWith("id:")) id = line.substring(3).strip();
                            else if (line.startsWith("data:")) data.append(line.substring(5).stripLeading());
                            else if (line.isEmpty()) {
                                if (kind.equals("ready")) ready.countDown();
                                if (kind.equals("decision")) received(json.readTree(data.toString()));
                                cursor = id;
                                kind = "";
                                data.setLength(0);
                            }
                        }
                    }
                }
            } catch (Exception error) {
                if (!closed.get()) {
                    failure = error;
                    pending.values().forEach(p -> p.milliseconds.completeExceptionally(error));
                }
            } finally { ready.countDown(); }
        }

        void received(JsonNode decision) {
            Pending sample = pending.get(decision.path("transaction_id").asText());
            if (sample == null) return;
            if (decision.path("degraded").asBoolean() || !decision.path("model").asText().equals("tabular_graph")) {
                sample.milliseconds.completeExceptionally(new IllegalStateException("Healthy graph-tabular path required"));
                return;
            }
            if (!decision.path("model_version").asText().equals(modelVersion) || !decision.path("feature_schema_hash").asText().equals(schemaHash)) {
                sample.milliseconds.completeExceptionally(new IllegalStateException("Model identity changed during benchmark"));
                return;
            }
            sample.decisions.add(decision.path("decision_id").asText());
            if (sample.decisions.size() == 2) sample.milliseconds.complete((System.nanoTime() - sample.started) / 1e6);
        }

        @Override public void close() throws Exception {
            closed.set(true);
            if (input != null) input.close();
            thread.join(5000);
            assertFalse(thread.isAlive(), "SSE reader failed to stop");
        }
    }

    private double transaction(StreamReader stream, long timestamp) throws Exception {
        String id = PrivacyCodec.hash(UUID.randomUUID().toString());
        String source = PrivacyCodec.hash(stream.tenant + ":source");
        String target = PrivacyCodec.hash(stream.tenant + ":target");
        String body = json.writeValueAsString(Map.of("transaction_id", id, "source", source, "target", target,
            "ts", timestamp, "amount", 100., "currency", "INR", "kind", "TRANSFER"));
        String signed = tokens.ingestion(stream.tenant, UUID.randomUUID().toString(), body);
        Pending pending = new Pending();
        stream.pending.put(id, pending);
        try {
            if (stream.failure != null) throw new IllegalStateException("SSE reader failed", stream.failure);
            producer.send("mulenet.transactions", stream.tenant + ":" + source, signed).get(10, TimeUnit.SECONDS);
            return pending.milliseconds.get(45, TimeUnit.SECONDS);
        } finally { stream.pending.remove(id); }
    }

    private Map<String, Object> kafkaLoad(int requests, int concurrency) throws Exception {
        String tenant = "bench_" + UUID.randomUUID().toString().replace("-", "");
        long timestamp = Instant.now().getEpochSecond();
        try (var stream = new StreamReader(tenant)) {
            for (int i = 0; i < 5; i++) transaction(stream, timestamp);
            ExecutorService pool = Executors.newFixedThreadPool(concurrency);
            List<Future<Double>> futures = new ArrayList<>();
            long started = System.nanoTime();
            try {
                for (int i = 0; i < requests; i++) futures.add(pool.submit(() -> transaction(stream, timestamp)));
                List<Double> durations = new ArrayList<>();
                for (var future : futures) durations.add(future.get(120, TimeUnit.SECONDS));
                assertNull(stream.failure);
                return Map.of("requests", requests, "concurrency", concurrency, "warmup_requests", 5,
                    "durations_ms", durations, "elapsed_seconds", (System.nanoTime() - started) / 1e9,
                    "degraded_decisions", 0, "decisions_per_transaction", 2);
            } finally { pool.shutdownNow(); assertTrue(pool.awaitTermination(10, TimeUnit.SECONDS)); }
        }
    }

    private JsonNode postMl(String endpoint, Object body, String tenant) throws Exception {
        var request = HttpRequest.newBuilder(URI.create("http://" + ml.getHost() + ":" + ml.getMappedPort(8000) + endpoint))
            .timeout(Duration.ofSeconds(20)).header("Authorization", "Bearer " + tokens.ml(tenant))
            .header("Content-Type", "application/json").POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body))).build();
        var response = client.send(request, HttpResponse.BodyHandlers.ofString());
        assertEquals(200, response.statusCode(), "ML endpoint failed");
        return json.readTree(response.body());
    }

    private Map<String, Object> httpLoad(int requests, int concurrency) throws Exception {
        String tenant = "bench_http";
        String account = "a".repeat(64);
        long timestamp = Instant.now().getEpochSecond();
        var receipt = postMl("/v1/snapshots", Map.of("complete_from", timestamp, "watermark", timestamp,
            "events", List.of(Map.of("transaction_id", "c".repeat(64), "source", "b".repeat(64), "target", account,
                "ts", timestamp, "amount", 100., "currency", "INR", "kind", "TRANSFER")), "accounts", List.of()), tenant);
        var body = Map.of("snapshot_id", receipt.path("snapshot_id").asText(), "account_id", account,
            "as_of", timestamp, "correlation_id", "benchmark-http");
        Callable<Double> sample = () -> {
            long started = System.nanoTime();
            var result = postMl("/v1/score", body, tenant);
            assertFalse(result.path("degraded").asBoolean());
            assertEquals("tabular_graph", result.path("model").asText());
            if (modelVersion == null) {
                modelVersion = result.path("model_version").asText();
                schemaHash = result.path("feature_schema_hash").asText();
            }
            assertEquals(modelVersion, result.path("model_version").asText());
            assertEquals(schemaHash, result.path("feature_schema_hash").asText());
            return (System.nanoTime() - started) / 1e6;
        };
        for (int i = 0; i < 5; i++) sample.call();
        ExecutorService pool = Executors.newFixedThreadPool(concurrency);
        long started = System.nanoTime();
        try {
            List<Callable<Double>> work = new ArrayList<>();
            for (int i = 0; i < requests; i++) work.add(sample);
            List<Double> durations = new ArrayList<>();
            for (var future : pool.invokeAll(work)) durations.add(future.get());
            return Map.of("requests", requests, "concurrency", concurrency, "warmup_requests", 5,
                "durations_ms", durations, "elapsed_seconds", (System.nanoTime() - started) / 1e9,
                "degraded_decisions", 0);
        } finally { pool.shutdownNow(); assertTrue(pool.awaitTermination(10, TimeUnit.SECONDS)); }
    }

    @Test void measureRealHttpAndKafkaToSseUnderSteadyAndBurstLoad() throws Exception {
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("data_provenance", "synthetic");
        report.put("model", "tabular_graph");
        report.put("scope", "Local single-broker hot-account workload; not a production SLO or GNN-path measurement");
        report.put("http_boundary", "Client call including JWT mint, HTTP, cache, features, model and response parsing; snapshot preparation excluded");
        report.put("kafka_boundary", "Immediately before producer.send to real HTTP SSE receipt of both committed account decisions; producer ack, Kafka, feature fetch, scoring, policy, persistence and SSE included; ingestion REST/outbox and network outside host excluded");
        report.put("http", Map.of("steady", httpLoad(100, 1), "burst", httpLoad(100, 8)));
        report.put("kafka_to_sse", Map.of("steady", kafkaLoad(100, 1), "burst", kafkaLoad(100, 8)));
        report.put("model_version", modelVersion);
        report.put("feature_schema_hash", schemaHash);
        report.put("ml_image_id", ml.getContainerInfo().getImageId());
        report.put("environment", Map.of("java", System.getProperty("java.runtime.version"),
            "os", System.getProperty("os.name"), "os_version", System.getProperty("os.version"),
            "processors", Runtime.getRuntime().availableProcessors()));
        Path output = Path.of("../.tools/pipeline-latency-raw.json");
        Files.createDirectories(output.getParent());
        Files.writeString(output, json.writerWithDefaultPrettyPrinter().writeValueAsString(report));
    }
}
