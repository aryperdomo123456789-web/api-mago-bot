BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS email_sender_identities (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT REFERENCES platform_tenants(id) ON DELETE CASCADE,
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(180) NOT NULL DEFAULT 'Mago Bot',
    reply_to VARCHAR(255),
    purpose VARCHAR(40) NOT NULL DEFAULT 'transactional',
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_email_sender_identity_tenant_email UNIQUE (tenant_id, sender_email),
    CONSTRAINT ck_email_sender_identity_purpose CHECK (purpose = 'transactional')
);
CREATE INDEX IF NOT EXISTS idx_email_sender_identities_tenant_status
    ON email_sender_identities(tenant_id, status);

CREATE TABLE IF NOT EXISTS email_deliveries (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT REFERENCES platform_tenants(id) ON DELETE SET NULL,
    user_id BIGINT REFERENCES panel_users(id) ON DELETE SET NULL,
    sender_identity_id BIGINT REFERENCES email_sender_identities(id) ON DELETE SET NULL,
    source_type VARCHAR(64) NOT NULL,
    source_id VARCHAR(180) NOT NULL,
    message_type VARCHAR(48) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(180),
    subject VARCHAR(255) NOT NULL,
    html_body TEXT NOT NULL,
    text_body TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    attempt_count BIGINT NOT NULL DEFAULT 0,
    provider_message_id VARCHAR(180),
    provider_event_id VARCHAR(180),
    error_code VARCHAR(80),
    error_message VARCHAR(512),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_email_delivery_source UNIQUE (source_type, source_id, message_type)
);
CREATE INDEX IF NOT EXISTS idx_email_deliveries_claim
    ON email_deliveries(status, next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_email_deliveries_recipient_created
    ON email_deliveries(recipient_email, created_at);
CREATE INDEX IF NOT EXISTS idx_email_deliveries_provider_message
    ON email_deliveries(provider_message_id);

CREATE TABLE IF NOT EXISTS email_suppressions (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    reason VARCHAR(40) NOT NULL,
    provider_event_id VARCHAR(180),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_email_suppressions_reason_created
    ON email_suppressions(reason, created_at);

CREATE TABLE IF NOT EXISTS email_provider_events (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    provider VARCHAR(40) NOT NULL DEFAULT 'resend',
    provider_event_id VARCHAR(180) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    email_id VARCHAR(180),
    recipient_email VARCHAR(255),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_email_provider_event UNIQUE (provider, provider_event_id)
);
CREATE INDEX IF NOT EXISTS idx_email_provider_events_email_id
    ON email_provider_events(email_id);

INSERT INTO schema_migrations (version)
VALUES ('0007_email_transacional')
ON CONFLICT (version) DO NOTHING;

COMMIT;
