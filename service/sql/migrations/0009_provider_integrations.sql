BEGIN;

CREATE TABLE IF NOT EXISTS provider_integrations (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    provider_type VARCHAR(32) NOT NULL,
    display_name VARCHAR(180) NOT NULL,
    external_resource_id VARCHAR(180) NOT NULL,
    credentials_encrypted TEXT NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    is_primary BOOLEAN NOT NULL DEFAULT TRUE,
    last_tested_at TIMESTAMPTZ NULL,
    last_error VARCHAR(512) NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by BIGINT NULL REFERENCES panel_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_provider_integrations_project_resource UNIQUE (project_id, provider_type, external_resource_id),
    CONSTRAINT ck_provider_integrations_provider CHECK (provider_type IN ('meta_cloud', 'evolution')),
    CONSTRAINT ck_provider_integrations_status CHECK (status IN ('active', 'disabled', 'error', 'testing'))
);

CREATE INDEX IF NOT EXISTS idx_provider_integrations_tenant_status
    ON provider_integrations (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_provider_integrations_project_provider
    ON provider_integrations (project_id, provider_type, status);

INSERT INTO schema_migrations (version, applied_at)
VALUES ('0009_provider_integrations', NOW())
ON CONFLICT (version) DO NOTHING;

COMMIT;
