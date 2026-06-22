-- ============================================================
-- V3: Add missing tables and case columns
-- ============================================================

-- 1. Add missing columns to cases table
ALTER TABLE cases ADD COLUMN IF NOT EXISTS accounts_analyzed INTEGER;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS accounts_flagged INTEGER;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS policy_decisions TEXT;

-- 2. Create complaints table
CREATE TABLE IF NOT EXISTS complaints (
    id                  BIGSERIAL PRIMARY KEY,
    complaint_id        VARCHAR(64) NOT NULL,
    utr                 VARCHAR(64) NOT NULL,
    amount              DOUBLE PRECISION NOT NULL,
    timestamp           TIMESTAMP NOT NULL,
    first_beneficiary   VARCHAR(64) NOT NULL
);

-- 3. Create investigator_actions table
CREATE TABLE IF NOT EXISTS investigator_actions (
    id                      BIGSERIAL PRIMARY KEY,
    case_id                 VARCHAR(64) NOT NULL,
    account_id              VARCHAR(64),
    action                  VARCHAR(64) NOT NULL,
    rationale               TEXT,
    performed_by            VARCHAR(128),
    timestamp               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    risk_score_at_action    DOUBLE PRECISION
);

-- 4. Create indexes for quick lookups
CREATE INDEX IF NOT EXISTS idx_investigator_actions_case ON investigator_actions(case_id);
CREATE INDEX IF NOT EXISTS idx_complaints_utr ON complaints(utr);
