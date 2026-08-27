package com.mulenet.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/**
 * DTO representing a request to get a fraud prediction.
 * Includes the account identifier and the full intake request payload.
 */
public class PredictionRequest {
    @NotBlank
    private String accountId;

    @NotNull
    private IntakeRequest intakeRequest;

    // getters and setters
    public String getAccountId() {
        return accountId;
    }

    public void setAccountId(String accountId) {
        this.accountId = accountId;
    }

    public IntakeRequest getIntakeRequest() {
        return intakeRequest;
    }

    public void setIntakeRequest(IntakeRequest intakeRequest) {
        this.intakeRequest = intakeRequest;
    }
}
