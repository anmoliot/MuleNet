package com.mulenet.api.platform;

import java.time.Instant;
import java.util.*;
import org.springframework.context.annotation.Profile;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@Profile("platform & demo")
public class DemoSeed {
    private final PlatformService platform;
    private final PrivacyCodec privacy;
    public DemoSeed(PlatformService platform, PrivacyCodec privacy) { this.platform = platform; this.privacy = privacy; }
    @PostMapping("/api/demo/seed")
    @PreAuthorize("hasRole('ADMIN')")
    public Map<String, Object> seed(Authentication auth) {
        String run = UUID.randomUUID().toString();
        long ts = Instant.now().getEpochSecond();
        List<Payment> payments = new ArrayList<>();
        for (int index = 0; index < 6; index++) {
            payments.add(new Payment("demo-" + run + "-" + index, "sim-source-" + index,
                "sim-relay-" + run, ts, 49000.0, "INR", "TRANSFER", "sim-device-" + run, null));
        }
        return Map.of("simulated", true, "transaction_ids", platform.enqueue(PlatformController.tenant(auth),
            privacy.token(PlatformController.tenant(auth), "actor", auth.getName()), payments));
    }
}
