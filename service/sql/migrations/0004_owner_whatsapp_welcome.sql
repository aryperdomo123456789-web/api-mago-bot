BEGIN;

ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS phone VARCHAR(40);
ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS whatsapp_opt_in BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS whatsapp_opt_in_source VARCHAR(180);
ALTER TABLE panel_users ADD COLUMN IF NOT EXISTS whatsapp_opt_in_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS owner_whatsapp_integrations (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    owner_user_id BIGINT NOT NULL REFERENCES panel_users(id) ON DELETE CASCADE,
    provider_type VARCHAR(32) NOT NULL DEFAULT 'meta_cloud',
    phone_number_id VARCHAR(32) NOT NULL,
    waba_id VARCHAR(32),
    access_token_encrypted TEXT,
    app_secret_encrypted TEXT,
    webhook_verify_token_encrypted TEXT,
    display_phone_number VARCHAR(40),
    verified_name VARCHAR(180),
    quality_rating VARCHAR(40),
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    welcome_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    welcome_template_name VARCHAR(512),
    welcome_template_language VARCHAR(32) NOT NULL DEFAULT 'pt_BR',
    opt_in_required BOOLEAN NOT NULL DEFAULT TRUE,
    last_checked_at TIMESTAMPTZ,
    last_error VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_owner_whatsapp_integration_owner UNIQUE (owner_user_id),
    CONSTRAINT ck_owner_whatsapp_provider CHECK (provider_type = 'meta_cloud'),
    CONSTRAINT ck_owner_whatsapp_phone CHECK (phone_number_id ~ '^[0-9]{8,32}$')
);

CREATE INDEX IF NOT EXISTS idx_owner_whatsapp_integrations_status
    ON owner_whatsapp_integrations(status);

CREATE TABLE IF NOT EXISTS owner_welcome_deliveries (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    integration_id BIGINT NOT NULL REFERENCES owner_whatsapp_integrations(id) ON DELETE CASCADE,
    source_type VARCHAR(64) NOT NULL,
    source_id VARCHAR(180) NOT NULL,
    recipient_phone VARCHAR(40) NOT NULL,
    recipient_name VARCHAR(180),
    opt_in BOOLEAN NOT NULL DEFAULT FALSE,
    opt_in_source VARCHAR(180),
    template_name VARCHAR(512) NOT NULL,
    template_language VARCHAR(32) NOT NULL DEFAULT 'pt_BR',
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    attempt_count BIGINT NOT NULL DEFAULT 0,
    provider_message_id VARCHAR(180),
    error_code VARCHAR(80),
    error_message VARCHAR(512),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_owner_welcome_source UNIQUE (integration_id, source_type, source_id),
    CONSTRAINT ck_owner_welcome_opt_in CHECK (opt_in = TRUE),
    CONSTRAINT ck_owner_welcome_status CHECK (status IN ('pending', 'sending', 'sent', 'failed', 'dead_letter', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_owner_welcome_status_next_attempt
    ON owner_welcome_deliveries(status, next_attempt_at);

CREATE INDEX IF NOT EXISTS idx_owner_welcome_recipient_created
    ON owner_welcome_deliveries(recipient_phone, created_at);

CREATE OR REPLACE FUNCTION touch_owner_whatsapp_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_owner_whatsapp_updated_at ON owner_whatsapp_integrations;
CREATE TRIGGER trg_owner_whatsapp_updated_at
BEFORE UPDATE ON owner_whatsapp_integrations
FOR EACH ROW EXECUTE FUNCTION touch_owner_whatsapp_updated_at();

DROP TRIGGER IF EXISTS trg_owner_welcome_updated_at ON owner_welcome_deliveries;
CREATE TRIGGER trg_owner_welcome_updated_at
BEFORE UPDATE ON owner_welcome_deliveries
FOR EACH ROW EXECUTE FUNCTION touch_owner_whatsapp_updated_at();

INSERT INTO schema_migrations(version)
VALUES ('0004_owner_whatsapp_welcome')
ON CONFLICT (version) DO NOTHING;

COMMIT;
