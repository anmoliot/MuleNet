package com.mulenet.api.platform;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.time.Duration;
import java.util.concurrent.TimeUnit;
import java.util.function.Supplier;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

@Component
@Profile("platform")
public class StageTelemetry {
    public enum Stage { SNAPSHOT_HTTP, SCORE_HTTP, KAFKA_PROCESS }
    private final MeterRegistry meters;
    public StageTelemetry(MeterRegistry meters) { this.meters = meters; }

    public <T> T timed(Stage stage, Supplier<T> action) {
        long started = System.nanoTime();
        boolean success = false;
        try {
            T result = action.get();
            success = true;
            return result;
        } finally { record(stage, started, success); }
    }

    public void record(Stage stage, long started, boolean success) {
        long elapsed = System.nanoTime() - started;
        if (elapsed < 0) throw new IllegalArgumentException("Stage clock is invalid");
        String outcome = success ? "success" : "error";
        Timer.builder("mulenet.pipeline.stage").tags("stage", stage.name().toLowerCase(java.util.Locale.ROOT), "outcome", outcome)
            .publishPercentileHistogram().serviceLevelObjectives(Duration.ofMillis(10), Duration.ofMillis(100), Duration.ofSeconds(1), Duration.ofSeconds(5))
            .register(meters).record(elapsed, TimeUnit.NANOSECONDS);
        LoggerFactory.getLogger(StageTelemetry.class).info("pipeline_stage stage={} outcome={} elapsed_ms={}", stage, outcome, elapsed / 1e6);
    }
}
