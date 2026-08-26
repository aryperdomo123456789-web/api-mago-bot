BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS evolution_instances (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    resource_id BIGINT UNIQUE REFERENCES provider_resources(id) ON DELETE SET NULL,
    instance_name VARCHAR(120) NOT NULL,
    provider_flavor VARCHAR(32) NOT NULL DEFAULT 'evolution_api',
    instance_token_encrypted TEXT,
    webhook_secret_encrypted TEXT,
    webhook_url VARCHAR(2048),
    subscribed_events JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'provisioning',
    jid VARCHAR(180),
    display_phone_number VARCHAR(40),
    last_status_check_at TIMESTAMPTZ,
    last_connected_at TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    qr_expires_at TIMESTAMPTZ,
    last_error_code VARCHAR(80),
    last_error_message VARCHAR(512),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by BIGINT REFERENCES panel_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_evolution_instances_project_name UNIQUE (project_id, instance_name),
    CONSTRAINT ck_evolution_instances_flavor CHECK (provider_flavor IN ('evolution_api', 'evolution_go')),
    CONSTRAINT ck_evolution_instances_status CHECK (status IN ('provisioning', 'created', 'qr_pending', 'pairing_pending', 'connected', 'syncing', 'disconnected', 'degraded', 'logged_out', 'suspended', 'failed', 'deleted'))
);

CREATE INDEX IF NOT EXISTS idx_evolution_instances_tenant_status
    ON evolution_instances(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_evolution_instances_project_status
    ON evolution_instances(project_id, status);
CREATE INDEX IF NOT EXISTS idx_evolution_instances_health
    ON evolution_instances(status, last_status_check_at);

CREATE TABLE IF NOT EXISTS evolution_instance_events (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    instance_id BIGINT NOT NULL REFERENCES evolution_instances(id) ON DELETE CASCADE,
    provider_event_id VARCHAR(180) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'accepted',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_evolution_instance_event UNIQUE (instance_id, provider_event_id)
);

CREATE INDEX IF NOT EXISTS idx_evolution_instance_events_instance_received
    ON evolution_instance_events(instance_id, received_at);
CREATE INDEX IF NOT EXISTS idx_evolution_instance_events_type_received
    ON evolution_instance_events(event_type, received_at);

INSERT INTO schema_migrations (version)
VALUES ('0008_evolution_instances')
ON CONFLICT (version) DO NOTHING;

COMMIT;
