-- ============================================================
-- V2: Add Case Comments Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS case_comments (
    id              BIGSERIAL PRIMARY KEY,
    case_id         VARCHAR(64) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    username        VARCHAR(128) NOT NULL,
    comment_text    TEXT NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_case_comments_case ON case_comments(case_id);
