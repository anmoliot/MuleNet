-- ============================================================
-- MuleNet Database Schema
-- PostgreSQL / SQLite compatible DDL
-- Version: 2.0.0
-- ============================================================

-- ------------------------------------------------------------
-- TABLE: accounts
-- Represents financial accounts under investigation
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
    id                  BIGSERIAL PRIMARY KEY,
    account_id          VARCHAR(64)  NOT NULL UNIQUE,
    account_type        VARCHAR(32)  NOT NULL DEFAULT 'SAVINGS',  -- SAVINGS, CURRENT, WALLET, CRYPTO
    bank_code           VARCHAR(16),
    ifsc_code           VARCHAR(16),
    holder_name         VARCHAR(256),
    kyc_status          VARCHAR(32)  DEFAULT 'PENDING',           -- PENDING, VERIFIED, FLAGGED
    account_age_days    INTEGER      DEFAULT 0,
    is_blacklisted      BOOLEAN      DEFAULT FALSE,
    risk_score          DECIMAL(5,2) DEFAULT 0.0,
    risk_level          VARCHAR(16)  DEFAULT 'MINIMAL',           -- MINIMAL, LOW, MODERATE, HIGH, CRITICAL
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_accounts_risk_score ON accounts(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_accounts_risk_level ON accounts(risk_level);
CREATE INDEX IF NOT EXISTS idx_accounts_blacklisted ON accounts(is_blacklisted);

-- ------------------------------------------------------------
-- TABLE: transactions
-- Records of financial transactions (UPI, NEFT, RTGS, IMPS, SWIFT)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id                  BIGSERIAL PRIMARY KEY,
    utr                 VARCHAR(64)  NOT NULL UNIQUE,
    transaction_type    VARCHAR(16)  NOT NULL DEFAULT 'UPI',      -- UPI, NEFT, RTGS, IMPS, SWIFT, WALLET
    amount              DECIMAL(18,2) NOT NULL,
    currency            VARCHAR(8)   DEFAULT 'INR',
    sender_account      VARCHAR(64)  NOT NULL,
    receiver_account    VARCHAR(64)  NOT NULL,
    transaction_time    TIMESTAMP    NOT NULL,
    device_id           VARCHAR(128),
    ip_address          VARCHAR(64),
    location_lat        DECIMAL(10,8),
    location_lng        DECIMAL(11,8),
    is_flagged          BOOLEAN      DEFAULT FALSE,
    flag_reason         TEXT,
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_txn_sender    FOREIGN KEY (sender_account)   REFERENCES accounts(account_id) ON DELETE SET NULL,
    CONSTRAINT fk_txn_receiver  FOREIGN KEY (receiver_account) REFERENCES accounts(account_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_sender    ON transactions(sender_account);
CREATE INDEX IF NOT EXISTS idx_transactions_receiver  ON transactions(receiver_account);
CREATE INDEX IF NOT EXISTS idx_transactions_time      ON transactions(transaction_time DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_flagged   ON transactions(is_flagged) WHERE is_flagged = TRUE;

-- ------------------------------------------------------------
-- TABLE: devices
-- Device fingerprints associated with account activity
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
    id                  BIGSERIAL PRIMARY KEY,
    device_id           VARCHAR(128) NOT NULL UNIQUE,
    device_type         VARCHAR(32)  DEFAULT 'MOBILE',            -- MOBILE, DESKTOP, TABLET
    os_type             VARCHAR(32),
    fingerprint_hash    VARCHAR(256),
    is_blacklisted      BOOLEAN      DEFAULT FALSE,
    sim_swap_flag       BOOLEAN      DEFAULT FALSE,
    shared_account_count INTEGER     DEFAULT 0,
    first_seen          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- TABLE: locations
-- Login and transaction location records
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS locations (
    id                  BIGSERIAL PRIMARY KEY,
    account_id          VARCHAR(64)  NOT NULL,
    latitude            DECIMAL(10,8) NOT NULL,
    longitude           DECIMAL(11,8) NOT NULL,
    city                VARCHAR(128),
    country             VARCHAR(64)  DEFAULT 'IN',
    ip_address          VARCHAR(64),
    is_tor              BOOLEAN      DEFAULT FALSE,
    is_vpn              BOOLEAN      DEFAULT FALSE,
    geo_velocity_flag   BOOLEAN      DEFAULT FALSE,
    recorded_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_locations_account ON locations(account_id);

-- ------------------------------------------------------------
-- TABLE: predictions
-- ML model prediction results per account per analysis run
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id                  BIGSERIAL PRIMARY KEY,
    account_id          VARCHAR(64)  NOT NULL,
    case_id             VARCHAR(64),
    model_version       VARCHAR(16)  NOT NULL,
    risk_score          DECIMAL(5,2) NOT NULL,
    risk_level          VARCHAR(16)  NOT NULL,
    fraud_probability   DECIMAL(5,4) NOT NULL,
    confidence          DECIMAL(5,4) NOT NULL,
    fast_path_score     DECIMAL(5,4),
    gnn_score           DECIMAL(5,4),
    topology_score      DECIMAL(5,2),
    anomaly_score       DECIMAL(5,4),
    external_uplift     DECIMAL(5,2),
    shap_explanation    JSONB,
    lime_explanation    JSONB,
    reason_codes        TEXT[],
    action_recommended  VARCHAR(32),
    predicted_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_account    ON predictions(account_id);
CREATE INDEX IF NOT EXISTS idx_predictions_case       ON predictions(case_id);
CREATE INDEX IF NOT EXISTS idx_predictions_risk_score ON predictions(risk_score DESC);

-- ------------------------------------------------------------
-- TABLE: alerts
-- Auto-generated alerts from high-risk accounts/transactions
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id                  BIGSERIAL PRIMARY KEY,
    alert_id            VARCHAR(64)  NOT NULL UNIQUE DEFAULT gen_random_uuid()::TEXT,
    alert_type          VARCHAR(64)  NOT NULL,           -- HIGH_RISK_ACCOUNT, FRAUD_RING, SMURFING, etc.
    severity            VARCHAR(16)  NOT NULL,           -- LOW, MEDIUM, HIGH, CRITICAL
    account_id          VARCHAR(64),
    case_id             VARCHAR(64),
    title               VARCHAR(256) NOT NULL,
    description         TEXT,
    risk_score          DECIMAL(5,2),
    status              VARCHAR(32)  DEFAULT 'OPEN',     -- OPEN, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE
    assigned_to         VARCHAR(128),
    resolved_at         TIMESTAMP,
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_severity   ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status     ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_account    ON alerts(account_id);

-- ------------------------------------------------------------
-- TABLE: cases
-- Investigation case management
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cases (
    id                  BIGSERIAL PRIMARY KEY,
    case_id             VARCHAR(64)  NOT NULL UNIQUE,
    complaint_id        VARCHAR(64),
    status              VARCHAR(32)  DEFAULT 'OPEN',     -- OPEN, UNDER_REVIEW, FROZEN, CLOSED, ESCALATED
    risk_score          DECIMAL(5,2) DEFAULT 0.0,
    risk_level          VARCHAR(16)  DEFAULT 'MINIMAL',
    ml_response         TEXT,                            -- Full JSON from ML service
    assigned_to         VARCHAR(128),
    supervisor          VARCHAR(128),
    case_notes          TEXT,
    escalation_reason   VARCHAR(512),
    complaint_amount    DECIMAL(18,2),
    recovery_estimate   DECIMAL(18,2),
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at         TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cases_status     ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_risk_score ON cases(risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_cases_assigned   ON cases(assigned_to);

-- ------------------------------------------------------------
-- TABLE: investigators
-- System user / investigator profiles
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS investigators (
    id                  BIGSERIAL PRIMARY KEY,
    username            VARCHAR(128) NOT NULL UNIQUE,
    email               VARCHAR(256) NOT NULL UNIQUE,
    full_name           VARCHAR(256) NOT NULL,
    role                VARCHAR(64)  NOT NULL DEFAULT 'INVESTIGATOR',   -- INVESTIGATOR, SUPERVISOR, FRAUD_ADMIN
    department          VARCHAR(128),
    badge_number        VARCHAR(64),
    is_active           BOOLEAN      DEFAULT TRUE,
    mfa_enabled         BOOLEAN      DEFAULT FALSE,
    last_login          TIMESTAMP,
    login_count         INTEGER      DEFAULT 0,
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- TABLE: audit_logs
-- Full audit trail for compliance and security monitoring
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id                  BIGSERIAL PRIMARY KEY,
    username            VARCHAR(128) NOT NULL,
    user_role           VARCHAR(64),
    action              VARCHAR(128) NOT NULL,  -- CASE_INTAKE, ACCOUNT_FREEZE, LOGIN, RETRAIN, etc.
    target_entity       VARCHAR(128),
    description         TEXT,
    ip_address          VARCHAR(64),
    user_agent          TEXT,
    request_id          VARCHAR(64),
    success             BOOLEAN      DEFAULT TRUE,
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_username   ON audit_logs(username);
CREATE INDEX IF NOT EXISTS idx_audit_action     ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created    ON audit_logs(created_at DESC);

-- ------------------------------------------------------------
-- TABLE: threat_intelligence
-- Stored watchlist and threat intelligence records
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS threat_intelligence (
    id                  BIGSERIAL PRIMARY KEY,
    ioc_type            VARCHAR(32)  NOT NULL,       -- account, device, ip, crypto_address
    ioc_value           VARCHAR(512) NOT NULL,
    source              VARCHAR(128) NOT NULL,        -- OFAC, I4C, NCRP, AbuseIPDB, etc.
    category            VARCHAR(64)  NOT NULL,        -- SANCTION_LIST, TOR_EXIT, HIGH_RISK_IP, etc.
    risk_weight         DECIMAL(5,2) DEFAULT 0.0,
    confidence          DECIMAL(4,3) DEFAULT 1.0,
    description         TEXT,
    is_active           BOOLEAN      DEFAULT TRUE,
    expires_at          TIMESTAMP,
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ti_ioc UNIQUE(ioc_type, ioc_value, source)
);

CREATE INDEX IF NOT EXISTS idx_ti_ioc_value  ON threat_intelligence(ioc_value);
CREATE INDEX IF NOT EXISTS idx_ti_category   ON threat_intelligence(category);
CREATE INDEX IF NOT EXISTS idx_ti_source     ON threat_intelligence(source);
CREATE INDEX IF NOT EXISTS idx_ti_active     ON threat_intelligence(is_active) WHERE is_active = TRUE;

-- ------------------------------------------------------------
-- Sample seed data
-- ------------------------------------------------------------
INSERT INTO investigators (username, email, full_name, role, department) VALUES
    ('admin', 'admin@mulenet.gov.in', 'System Administrator', 'FRAUD_ADMIN', 'Cybercrime Intelligence'),
    ('investigator1', 'inv1@mulenet.gov.in', 'Senior Investigator', 'INVESTIGATOR', 'Financial Crimes Unit'),
    ('supervisor1', 'sup1@mulenet.gov.in', 'Senior Supervisor', 'SUPERVISOR', 'AML Operations')
ON CONFLICT (username) DO NOTHING;

INSERT INTO threat_intelligence (ioc_type, ioc_value, source, category, risk_weight, description) VALUES
    ('account', 'AC-MULE-001', 'I4C', 'I4C_SUSPECT_REGISTRY', 35.0, 'Confirmed mule account from I4C registry'),
    ('account', 'AC-FRAUD-RING-01', 'NCRP', 'NCRP_COMPLAINT', 25.0, '8 NCRP complaints linked to account'),
    ('ip', '185.220.101.1', 'AbuseIPDB', 'HIGH_RISK_IP', 15.0, 'Known high-risk IP from AbuseIPDB'),
    ('ip', '176.10.99.200', 'TorProject', 'TOR_EXIT_NODE', 20.0, 'TOR network exit node')
ON CONFLICT (ioc_type, ioc_value, source) DO NOTHING;
