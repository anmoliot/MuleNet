package com.mulenet.api.platform;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ReviewPolicyTest {
    @Test void initialPolicyUsesValidationUnlessCostRequiresMoreCaution() {
        var policy = ReviewPolicy.initial();
        assertEquals(900, policy.maxHoldSeconds());
        assertEquals(0.75, policy.threshold(0.75));
        assertEquals(1000.0 / 11000.0, policy.threshold(0.01));
    }

    @Test void explicitReviewedThresholdReplacesValidationButNotCostFloor() {
        var policy = new ReviewPolicy(300, 0.4, 1000, 1000);
        assertEquals(0.5, policy.threshold(0.9));
        var stricter = new ReviewPolicy(300, 0.8, 1000, 1000);
        assertEquals(0.8, stricter.threshold(0.1));
    }
}
