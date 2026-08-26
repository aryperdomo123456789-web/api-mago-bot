BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(120) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE panel_users
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ NULL;

CREATE TABLE IF NOT EXISTS platform_tenants (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    slug VARCHAR(80) NOT NULL UNIQUE,
    legal_name VARCHAR(180) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    plan_slug VARCHAR(64) NOT NULL DEFAULT 'start',
    billing_email VARCHAR(255),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_platform_tenants_status ON platform_tenants(status);

CREATE TABLE IF NOT EXISTS tenant_memberships (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES panel_users(id) ON DELETE CASCADE,
    role VARCHAR(40) NOT NULL DEFAULT 'tenant_readonly',
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    invited_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenant_membership_tenant_user UNIQUE (tenant_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_tenant_memberships_user ON tenant_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_tenant_memberships_tenant_role ON tenant_memberships(tenant_id, role);

CREATE TABLE IF NOT EXISTS platform_sessions (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    session_hash VARCHAR(64) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL REFERENCES panel_users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    ip_address VARCHAR(64),
    user_agent VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_platform_sessions_user_active ON platform_sessions(user_id, revoked_at, expires_at);
CREATE INDEX IF NOT EXISTS idx_platform_sessions_expires_at ON platform_sessions(expires_at);

CREATE TABLE IF NOT EXISTS platform_projects (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    name VARCHAR(180) NOT NULL,
    slug VARCHAR(80) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    provider_type VARCHAR(32),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_platform_projects_tenant_slug UNIQUE (tenant_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_platform_projects_tenant_status ON platform_projects(tenant_id, status);

CREATE TABLE IF NOT EXISTS platform_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    plan_slug VARCHAR(64) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'trialing',
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    external_customer_id VARCHAR(180),
    external_subscription_id VARCHAR(180),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_platform_subscriptions_tenant_status ON platform_subscriptions(tenant_id, status);

CREATE TABLE IF NOT EXISTS provider_resources (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    provider_type VARCHAR(32) NOT NULL,
    provider_resource_id VARCHAR(180),
    status VARCHAR(32) NOT NULL DEFAULT 'requested',
    display_name VARCHAR(180) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_provider_resources_tenant_status ON provider_resources(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_provider_resources_provider_id ON provider_resources(provider_type, provider_resource_id);

CREATE TABLE IF NOT EXISTS service_api_keys (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT REFERENCES platform_projects(id) ON DELETE SET NULL,
    prefix VARCHAR(24) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_by BIGINT REFERENCES panel_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_service_api_keys_tenant_status ON service_api_keys(tenant_id, status);

CREATE TABLE IF NOT EXISTS idempotency_records (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    user_id BIGINT REFERENCES panel_users(id) ON DELETE SET NULL,
    idempotency_key VARCHAR(160) NOT NULL,
    endpoint VARCHAR(180) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    status_code BIGINT,
    response_json JSONB,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_idempotency_tenant_key_endpoint UNIQUE (tenant_id, idempotency_key, endpoint)
);
CREATE INDEX IF NOT EXISTS idx_idempotency_expires_at ON idempotency_records(expires_at);

CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    tenant_id BIGINT REFERENCES platform_tenants(id) ON DELETE SET NULL,
    actor_user_id BIGINT REFERENCES panel_users(id) ON DELETE SET NULL,
    action VARCHAR(80) NOT NULL,
    resource_type VARCHAR(80),
    resource_id VARCHAR(180),
    outcome VARCHAR(24) NOT NULL DEFAULT 'success',
    request_id VARCHAR(80),
    ip_address VARCHAR(64),
    user_agent VARCHAR(512),
    reason VARCHAR(512),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_created_at ON audit_events(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor_created_at ON audit_events(actor_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_events_action_created_at ON audit_events(action, created_at);

CREATE TABLE IF NOT EXISTS auth_tokens (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    user_id BIGINT NOT NULL REFERENCES panel_users(id) ON DELETE CASCADE,
    purpose VARCHAR(32) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_purpose ON auth_tokens(user_id, purpose, used_at);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires_at ON auth_tokens(expires_at);


-- Usage counters are scoped by tenant and time window for atomic quota enforcement.
CREATE TABLE IF NOT EXISTS usage_counters (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    window_start TIMESTAMPTZ NOT NULL,
    metric VARCHAR(80) NOT NULL,
    value BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_usage_counter_tenant_window_metric UNIQUE (tenant_id, window_start, metric)
);
CREATE INDEX IF NOT EXISTS idx_usage_counters_tenant_metric ON usage_counters(tenant_id, metric, window_start);

CREATE TABLE IF NOT EXISTS outbound_messages (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    resource_id BIGINT REFERENCES provider_resources(id) ON DELETE SET NULL,
    provider_type VARCHAR(32) NOT NULL,
    idempotency_key VARCHAR(160) NOT NULL,
    recipient VARCHAR(32) NOT NULL,
    message_type VARCHAR(32) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'accepted',
    provider_message_id VARCHAR(180),
    error_code VARCHAR(80),
    error_message VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_outbound_messages_tenant_idempotency UNIQUE (tenant_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_outbound_messages_tenant_status ON outbound_messages(tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_outbound_messages_provider_id ON outbound_messages(provider_type, provider_message_id);


CREATE TABLE IF NOT EXISTS webhook_events (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    provider_type VARCHAR(32) NOT NULL,
    provider_event_id VARCHAR(180) NOT NULL,
    tenant_id BIGINT REFERENCES platform_tenants(id) ON DELETE SET NULL,
    resource_id BIGINT REFERENCES provider_resources(id) ON DELETE SET NULL,
    event_type VARCHAR(80) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'accepted',
    attempts BIGINT NOT NULL DEFAULT 0,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    CONSTRAINT uq_webhook_events_provider_event UNIQUE (provider_type, provider_event_id)
);
CREATE INDEX IF NOT EXISTS idx_webhook_events_status_received_at ON webhook_events(status, received_at);
CREATE INDEX IF NOT EXISTS idx_webhook_events_tenant_received_at ON webhook_events(tenant_id, received_at);


CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    endpoint_url VARCHAR(2048) NOT NULL,
    secret_encrypted TEXT NOT NULL,
    events JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    failure_count BIGINT NOT NULL DEFAULT 0,
    last_delivery_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_tenant_status ON webhook_subscriptions(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_project_status ON webhook_subscriptions(project_id, status);


CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    subscription_id BIGINT NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
    event_id BIGINT NOT NULL REFERENCES webhook_events(id) ON DELETE CASCADE,
    status VARCHAR(24) NOT NULL DEFAULT 'pending',
    attempt_count BIGINT NOT NULL DEFAULT 0,
    response_code BIGINT,
    last_error VARCHAR(512),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_webhook_deliveries_subscription_event UNIQUE (subscription_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status_next_attempt ON webhook_deliveries(status, next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_subscription_status ON webhook_deliveries(subscription_id, status);

INSERT INTO schema_migrations(version) VALUES ('0001_platform_foundation') ON CONFLICT (version) DO NOTHING;

COMMIT;
