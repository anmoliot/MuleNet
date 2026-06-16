package com.mulenet.api.dto;

import com.mulenet.api.model.Complaint;
import com.mulenet.api.model.Transaction;
import java.util.List;

public class IntakeRequest {
    private Complaint complaint;
    private List<Transaction> transactions;

    public IntakeRequest() {}

    public IntakeRequest(Complaint complaint, List<Transaction> transactions) {
        this.complaint = complaint;
        this.transactions = transactions;
    }

    public Complaint getComplaint() {
        return complaint;
    }

    public void setComplaint(Complaint complaint) {
        this.complaint = complaint;
    }

    public List<Transaction> getTransactions() {
        return transactions;
    }

    public void setTransactions(List<Transaction> transactions) {
        this.transactions = transactions;
    }
}
