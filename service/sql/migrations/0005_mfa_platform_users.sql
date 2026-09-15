BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS mfa_secret_encrypted TEXT;
ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS mfa_recovery_hashes JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS mfa_last_used_counter BIGINT;
ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS mfa_enrolled_at TIMESTAMPTZ;

INSERT INTO schema_migrations (version)
VALUES ('0005_mfa_platform_users')
ON CONFLICT (version) DO NOTHING;

COMMIT;
