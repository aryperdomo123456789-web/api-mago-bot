BEGIN;

ALTER TABLE idempotency_records
    ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES platform_projects(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_idempotency_project_lookup
    ON idempotency_records(project_id, idempotency_key, endpoint);
ALTER TABLE idempotency_records
    DROP CONSTRAINT IF EXISTS uq_idempotency_tenant_key_endpoint;
CREATE UNIQUE INDEX IF NOT EXISTS uq_idempotency_project_key_endpoint
    ON idempotency_records(tenant_id, project_id, idempotency_key, endpoint);

ALTER TABLE outbound_messages
    DROP CONSTRAINT IF EXISTS uq_outbound_messages_tenant_idempotency;
CREATE UNIQUE INDEX IF NOT EXISTS uq_outbound_messages_project_idempotency
    ON outbound_messages(tenant_id, project_id, idempotency_key);

CREATE TABLE IF NOT EXISTS platform_operations (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    api_key_id BIGINT REFERENCES service_api_keys(id) ON DELETE SET NULL,
    actor_user_id BIGINT REFERENCES panel_users(id) ON DELETE SET NULL,
    kind VARCHAR(80) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    idempotency_key VARCHAR(160) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    response JSONB,
    error JSONB,
    attempt_count BIGINT NOT NULL DEFAULT 0,
    created_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    start_time TIMESTAMPTZ,
    update_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    complete_time TIMESTAMPTZ,
    expire_time TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '30 days'),
    heartbeat_time TIMESTAMPTZ,
    CONSTRAINT uq_platform_operations_idempotency UNIQUE (tenant_id, project_id, kind, idempotency_key),
    CONSTRAINT ck_platform_operations_status CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancel_requested', 'cancelled', 'aborted', 'expired')),
    CONSTRAINT ck_platform_operations_done_payload CHECK (
        (status IN ('succeeded') AND response IS NOT NULL AND error IS NULL)
        OR (status IN ('failed', 'aborted', 'cancelled') AND error IS NOT NULL AND response IS NULL)
        OR (status IN ('queued', 'running', 'cancel_requested', 'expired'))
    )
);

CREATE INDEX IF NOT EXISTS idx_platform_operations_project_status
    ON platform_operations(project_id, status, update_time DESC);
CREATE INDEX IF NOT EXISTS idx_platform_operations_tenant_status
    ON platform_operations(tenant_id, status, update_time DESC);
CREATE INDEX IF NOT EXISTS idx_platform_operations_expire_time
    ON platform_operations(expire_time);
CREATE INDEX IF NOT EXISTS idx_platform_operations_heartbeat_time
    ON platform_operations(status, heartbeat_time);

INSERT INTO schema_migrations (version)
VALUES ('0011_operations')
ON CONFLICT (version) DO NOTHING;

COMMIT;
