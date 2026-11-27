package com.mulenet.api.platform;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.*;
import org.testcontainers.junit.jupiter.Testcontainers;
import static org.awaitility.Awaitility.await;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles({"platform", "demo"})
@Testcontainers
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class PlatformBrowserTest extends PlatformTestStack {
    @LocalServerPort int port;
    @Autowired ObjectMapper json;
    @Autowired PlatformService platform;

    @DynamicPropertySource static void browserOrigin(DynamicPropertyRegistry registry) {
        registry.add("mulenet.cors-origins", () -> "http://127.0.0.1:5181");
    }

    @Test void actualBrowserLoginEvidenceReviewReleaseAndPolicy() throws Exception {
        long time = Instant.now().getEpochSecond();
        platform.enqueue("demo", "browser-fixture", List.of(new Payment("ui-healthy", "ui-source", "ui-target", time, 49000., "INR", "TRANSFER", null, null)));
        await().atMost(Duration.ofSeconds(50)).until(() -> platform.decisions("demo").size() == 2);
        for (var row : platform.decisions("demo")) assertFalse(json.readTree((String) row.get("result")).path("degraded").asBoolean());
        assertTrue(platform.drift("demo").path("windows").isArray());
        ml.stop();
        platform.enqueue("demo", "browser-fixture", List.of(new Payment("ui-review", "ui-source", "ui-next", time + 1, 100., "INR", "TRANSFER", null, null)));
        await().atMost(Duration.ofSeconds(50)).until(() -> platform.decisions("demo").size() == 4);
        var held = platform.decisions("demo").stream().filter(row -> {
            try { return json.readTree((String) row.get("result")).path("degraded").asBoolean(); }
            catch (Exception failure) { throw new IllegalStateException(failure); }
        }).toList();
        assertEquals(2, held.size());
        int policyVersion = ((Number) platform.policy("demo").get("version")).intValue();
        String host = System.getenv().getOrDefault("MULENET_BROWSER_BACKEND_HOST", "127.0.0.1");
        if (!host.matches("[0-9.]+")) throw new IllegalArgumentException("An explicit local test IPv4 address is required");
        Map<String, Object> fixture = Map.of("backend", "http://" + host + ":" + port, "local_wsl_bridge", !host.equals("127.0.0.1"), "passwords", PASSWORDS,
            "decisions", Map.of("desktop", held.get(0).get("decision_id"), "mobile", held.get(1).get("decision_id")));
        String node = System.getenv().getOrDefault("MULENET_BROWSER_NODE", "node");
        Process child = new ProcessBuilder(node, "scripts/run-platform-browser.mjs")
            .directory(Path.of("../frontend").toFile()).redirectErrorStream(true)
            .redirectOutput(Path.of("../.tools/platform-browser-driver.log").toFile()).start();
        try (var output = child.getOutputStream()) { output.write(json.writeValueAsBytes(fixture)); }
        if (!child.waitFor(400, TimeUnit.SECONDS)) {
            child.descendants().forEach(handle -> handle.destroyForcibly());
            child.destroyForcibly();
            throw new AssertionError("Browser acceptance timed out");
        }
        assertEquals(0, child.exitValue(), "Browser acceptance failed; see the redacted local browser receipt");
        var receipt = json.readTree(Files.readString(Path.of("../reports/frontend-platform.json"), StandardCharsets.UTF_8));
        assertTrue(receipt.path("pass").asBoolean());
        for (var row : held) assertEquals("RELEASED", platform.decision("demo", (String) row.get("decision_id")).get("status"));
        assertEquals(policyVersion + 2, ((Number) platform.policy("demo").get("version")).intValue());
    }
}
