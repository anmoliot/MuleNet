package com.mulenet.api.platform;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class StageTelemetryTest {
    @Test void recordsSuccessfulAndFailedCallsWithoutHighCardinalityLabels() {
        var meters = new SimpleMeterRegistry();
        var telemetry = new StageTelemetry(meters);
        assertEquals("ok", telemetry.timed(StageTelemetry.Stage.SCORE_HTTP, () -> "ok"));
        assertThrows(IllegalStateException.class, () -> telemetry.timed(StageTelemetry.Stage.SCORE_HTTP, () -> { throw new IllegalStateException("fixture-only"); }));
        assertEquals(1, meters.get("mulenet.pipeline.stage").tag("outcome", "success").timer().count());
        assertEquals(1, meters.get("mulenet.pipeline.stage").tag("outcome", "error").timer().count());
        for (var meter : meters.getMeters()) {
            assertTrue(meter.getId().getTags().stream().allMatch(t -> java.util.Set.of("stage", "outcome", "le").contains(t.getKey())), meter.getId().toString());
            for (var tag : meter.getId().getTags()) if (tag.getKey().equals("le"))
                assertTrue(java.util.Set.of(0.01, 0.1, 1.0, 5.0).contains(Double.parseDouble(tag.getValue())), meter.getId().toString());
        }
        assertThrows(IllegalArgumentException.class, () -> telemetry.record(StageTelemetry.Stage.KAFKA_PROCESS, System.nanoTime() + 1_000_000_000L, true));
    }
}
