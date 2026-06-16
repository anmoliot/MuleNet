package com.mulenet.api;

import com.mulenet.api.dto.IntakeRequest;
import com.mulenet.api.model.Complaint;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class ValidationTest {

    private static Validator validator;

    @BeforeAll
    public static void setUp() {
        ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @Test
    public void testInvalidIntakeRequestMissingComplaintAndTxns() {
        IntakeRequest request = new IntakeRequest(null, null);
        Set<ConstraintViolation<IntakeRequest>> violations = validator.validate(request);
        
        assertFalse(violations.isEmpty(), "Validation violations should be reported for null parameters");
    }

    @Test
    public void testInvalidComplaintAmount() {
        Complaint complaint = new Complaint();
        complaint.setComplaintId("C1");
        complaint.setUtr("UTR00000000");
        complaint.setAmount(-100.0); // Invalid: negative amount
        complaint.setFirstBeneficiary("AC-1234");
        
        Set<ConstraintViolation<Complaint>> violations = validator.validate(complaint);
        assertFalse(violations.isEmpty(), "Negative complaint amounts should fail validation");
    }

    @Test
    public void testValidComplaint() {
        Complaint complaint = new Complaint();
        complaint.setComplaintId("C123");
        complaint.setUtr("UTR123456789");
        complaint.setAmount(5000.00);
        complaint.setTimestamp(java.time.LocalDateTime.now());
        complaint.setFirstBeneficiary("AC-1234");

        Set<ConstraintViolation<Complaint>> violations = validator.validate(complaint);
        assertTrue(violations.isEmpty(), "Valid complaints should pass validation");
    }
}
