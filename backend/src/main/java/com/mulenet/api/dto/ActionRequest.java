package com.mulenet.api.dto;

import com.mulenet.api.model.InvestigatorAction;

/**
 * Request body for recording an investigator action on a case.
 */
public class ActionRequest {

    private String accountId;
    private InvestigatorAction.ActionType action;
    private String rationale;
    private String performedBy;

    public ActionRequest() {}

    public String getAccountId() { return accountId; }
    public void setAccountId(String accountId) { this.accountId = accountId; }

    public InvestigatorAction.ActionType getAction() { return action; }
    public void setAction(InvestigatorAction.ActionType action) { this.action = action; }

    public String getRationale() { return rationale; }
    public void setRationale(String rationale) { this.rationale = rationale; }

    public String getPerformedBy() { return performedBy; }
    public void setPerformedBy(String performedBy) { this.performedBy = performedBy; }
}
