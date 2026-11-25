package com.mulenet.api.platform;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;

public record Payment(
    @JsonProperty("transaction_id") @NotBlank @Size(max = 256) String transactionId,
    @NotBlank @Size(max = 256) String source,
    @NotBlank @Size(max = 256) String target,
    @PositiveOrZero long ts,
    @NotNull @DecimalMin("0.01") @DecimalMax("1000000000000") Double amount,
    @NotBlank @Pattern(regexp = "INR") String currency,
    @NotBlank @Pattern(regexp = "TRANSFER|PAYMENT|DEBIT|CASH_IN|CASH_OUT|ACH") String kind,
    @JsonProperty("device_id") @Size(max = 256) String deviceId,
    @JsonProperty("ip_address") @Size(max = 256) String ipAddress
) {}
