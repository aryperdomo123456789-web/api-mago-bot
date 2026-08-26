BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS customer_profiles (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    display_name VARCHAR(180),
    external_ref VARCHAR(180),
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_customer_profiles_tenant_status ON customer_profiles(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_customer_profiles_tenant_external_ref ON customer_profiles(tenant_id, external_ref);

CREATE TABLE IF NOT EXISTS customer_identities (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    customer_profile_id BIGINT NOT NULL REFERENCES customer_profiles(id) ON DELETE CASCADE,
    identity_type VARCHAR(32) NOT NULL,
    normalized_value VARCHAR(255) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT false,
    verified_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_customer_identity_tenant_type_value UNIQUE(tenant_id, identity_type, normalized_value)
);
CREATE INDEX IF NOT EXISTS idx_customer_identities_profile ON customer_identities(customer_profile_id);
CREATE INDEX IF NOT EXISTS idx_customer_identities_tenant_channel ON customer_identities(tenant_id, channel);

CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    customer_profile_id BIGINT NOT NULL REFERENCES customer_profiles(id) ON DELETE RESTRICT,
    primary_channel VARCHAR(32) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    subject VARCHAR(255),
    external_ref VARCHAR(180),
    last_event_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_status_updated ON conversations(tenant_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_conversations_project_customer ON conversations(project_id, customer_profile_id);
CREATE INDEX IF NOT EXISTS idx_conversations_tenant_external_ref ON conversations(tenant_id, external_ref);

CREATE TABLE IF NOT EXISTS conversation_participants (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_profile_id BIGINT REFERENCES customer_profiles(id) ON DELETE SET NULL,
    participant_type VARCHAR(32) NOT NULL,
    participant_ref VARCHAR(180) NOT NULL,
    channel VARCHAR(32),
    address VARCHAR(255),
    display_name VARCHAR(180),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_conversation_participant_ref UNIQUE(conversation_id, participant_type, participant_ref)
);
CREATE INDEX IF NOT EXISTS idx_conversation_participants_conversation ON conversation_participants(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_participants_customer ON conversation_participants(customer_profile_id);

CREATE TABLE IF NOT EXISTS conversation_events (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_profile_id BIGINT REFERENCES customer_profiles(id) ON DELETE SET NULL,
    event_type VARCHAR(32) NOT NULL,
    direction VARCHAR(24) NOT NULL DEFAULT 'system',
    channel VARCHAR(32),
    actor_type VARCHAR(32) NOT NULL DEFAULT 'system',
    provider_type VARCHAR(32),
    provider_event_id VARCHAR(180),
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_conversation_event_provider UNIQUE(tenant_id, provider_type, provider_event_id)
);
CREATE INDEX IF NOT EXISTS idx_conversation_events_conversation_created ON conversation_events(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_events_tenant_type_created ON conversation_events(tenant_id, event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_events_customer_created ON conversation_events(customer_profile_id, created_at);

INSERT INTO schema_migrations(version)
VALUES ('0002_conversation_core')
ON CONFLICT (version) DO NOTHING;

COMMIT;
