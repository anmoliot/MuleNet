CREATE TABLE platform_tenants (
    tenant VARCHAR(128) PRIMARY KEY,
    watermark BIGINT NOT NULL DEFAULT 0,
    audit_sequence BIGINT NOT NULL DEFAULT 0,
    audit_head VARCHAR(64) NOT NULL DEFAULT 'GENESIS'
);
CREATE TABLE platform_ledger (
    tenant VARCHAR(128) NOT NULL REFERENCES platform_tenants(tenant),
    transaction_id VARCHAR(64) NOT NULL,
    source_account VARCHAR(64) NOT NULL,
    target_account VARCHAR(64) NOT NULL,
    event_time BIGINT NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (tenant, transaction_id)
);
CREATE INDEX platform_ledger_time ON platform_ledger(tenant, event_time);
CREATE TABLE platform_vault (
    tenant VARCHAR(128) NOT NULL,
    transaction_id VARCHAR(64) NOT NULL,
    ciphertext TEXT NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    created_at BIGINT NOT NULL,
    PRIMARY KEY (tenant, transaction_id)
);
CREATE TABLE platform_policies (
    tenant VARCHAR(128) NOT NULL REFERENCES platform_tenants(tenant),
    version INTEGER NOT NULL,
    config TEXT NOT NULL,
    actor VARCHAR(128) NOT NULL,
    created_at BIGINT NOT NULL,
    PRIMARY KEY (tenant, version)
);
CREATE TABLE platform_decisions (
    decision_id VARCHAR(64) PRIMARY KEY,
    tenant VARCHAR(128) NOT NULL REFERENCES platform_tenants(tenant),
    transaction_id VARCHAR(64) NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    as_of BIGINT NOT NULL,
    result TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    assignee VARCHAR(128),
    version INTEGER NOT NULL DEFAULT 1,
    expires_at BIGINT,
    created_at BIGINT NOT NULL,
    UNIQUE (tenant, transaction_id, account_id)
);
CREATE INDEX platform_decisions_queue ON platform_decisions(tenant, created_at);
CREATE TABLE platform_outbox (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(64) NOT NULL UNIQUE,
    tenant VARCHAR(128) NOT NULL,
    partition_key VARCHAR(256) NOT NULL,
    kind VARCHAR(32) NOT NULL,
    payload TEXT NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at BIGINT NOT NULL
);
CREATE INDEX platform_outbox_pending ON platform_outbox(published, id);
CREATE TABLE platform_audit (
    tenant VARCHAR(128) NOT NULL REFERENCES platform_tenants(tenant),
    sequence BIGINT NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    entry_hash VARCHAR(64) NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (tenant, sequence)
);
CREATE TABLE platform_feedback (
    tenant VARCHAR(128) NOT NULL,
    decision_id VARCHAR(64) NOT NULL REFERENCES platform_decisions(decision_id),
    reviewer VARCHAR(128) NOT NULL,
    reviewer_role VARCHAR(16) NOT NULL,
    fraudulent BOOLEAN NOT NULL,
    evidence TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    PRIMARY KEY (tenant, decision_id, reviewer)
);

CREATE FUNCTION platform_audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Audit entries are append-only';
END;
$$;
CREATE TRIGGER platform_audit_immutable BEFORE UPDATE OR DELETE ON platform_audit
    FOR EACH ROW EXECUTE FUNCTION platform_audit_immutable();

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mulenet_runtime') THEN
        REVOKE UPDATE,DELETE ON platform_audit,platform_policies FROM mulenet_runtime;
        REVOKE UPDATE ON platform_decisions FROM mulenet_runtime;
        GRANT UPDATE(status,assignee,version,expires_at) ON platform_decisions TO mulenet_runtime;
    END IF;
END $$;
