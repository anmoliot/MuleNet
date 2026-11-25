package com.mulenet.api.platform;

import jakarta.validation.constraints.*;

public record ReviewPolicy(
    @Positive @Max(86400) int maxHoldSeconds,
    @DecimalMin("0") @DecimalMax("1") Double reviewThreshold,
    @Positive double falseFreezeCostInr,
    @Positive double missedRiskCostInr
) {
    public static ReviewPolicy initial() { return new ReviewPolicy(900, null, 1000, 10000); }
    public double threshold(double validationThreshold) {
        double costThreshold = falseFreezeCostInr / (falseFreezeCostInr + missedRiskCostInr);
        return Math.max(costThreshold, reviewThreshold == null ? validationThreshold : reviewThreshold);
    }
}
