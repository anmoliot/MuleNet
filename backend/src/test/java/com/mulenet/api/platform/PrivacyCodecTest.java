package com.mulenet.api.platform;

import java.util.Base64;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class PrivacyCodecTest {
    private final String key = Base64.getEncoder().encodeToString(new byte[32]);
    @Test void domainAndTenantSeparatedAndAuthenticated() {
        PrivacyCodec codec = new PrivacyCodec(key, key);
        String token = codec.token("tenant-a", "account", "raw-account");
        assertEquals(token, codec.token("tenant-a", "account", "raw-account"));
        assertNotEquals(token, codec.token("tenant-b", "account", "raw-account"));
        assertNotEquals(token, codec.token("tenant-a", "device", "raw-account"));
        String encrypted = codec.encrypt("tenant-a", "sensitive-value");
        assertFalse(encrypted.contains("sensitive-value"));
        assertNotEquals(encrypted, codec.encrypt("tenant-a", "sensitive-value"));
        assertEquals("sensitive-value", codec.decrypt("tenant-a", encrypted));
        assertThrows(IllegalArgumentException.class, () -> codec.decrypt("tenant-b", encrypted));
        assertThrows(IllegalArgumentException.class, () -> codec.decrypt("tenant-a", encrypted + "x"));
    }
    @Test void costBoundAndValidationThresholdAreExplicit() {
        ReviewPolicy policy = ReviewPolicy.initial();
        assertEquals(.5, policy.threshold(.5));
        assertTrue(policy.threshold(0) > 0);
        assertTrue(policy.threshold(Math.nextUp(1.0)) > 1.0);
    }
}
