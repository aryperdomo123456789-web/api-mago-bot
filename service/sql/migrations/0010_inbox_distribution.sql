CREATE TABLE IF NOT EXISTS inbox_queues (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    slug VARCHAR(80) NOT NULL,
    display_name VARCHAR(120) NOT NULL,
    routing_strategy VARCHAR(32) NOT NULL DEFAULT 'manual',
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_inbox_queues_project_slug UNIQUE (project_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_inbox_queues_tenant_status ON inbox_queues(tenant_id, status);

CREATE TABLE IF NOT EXISTS conversation_assignments (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    conversation_id BIGINT NOT NULL UNIQUE REFERENCES conversations(id) ON DELETE CASCADE,
    queue_id BIGINT REFERENCES inbox_queues(id) ON DELETE SET NULL,
    assignee_user_id BIGINT REFERENCES panel_users(id) ON DELETE SET NULL,
    state VARCHAR(24) NOT NULL DEFAULT 'unassigned',
    snoozed_until TIMESTAMPTZ,
    claimed_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversation_assignments_tenant_state ON conversation_assignments(tenant_id, state, updated_at);
CREATE INDEX IF NOT EXISTS idx_conversation_assignments_queue_state ON conversation_assignments(queue_id, state, updated_at);
CREATE INDEX IF NOT EXISTS idx_conversation_assignments_assignee_state ON conversation_assignments(assignee_user_id, state, updated_at);

INSERT INTO schema_migrations(version)
VALUES ('0010_inbox_distribution.sql')
ON CONFLICT (version) DO NOTHING;
