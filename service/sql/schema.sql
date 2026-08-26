CREATE TABLE IF NOT EXISTS license_projects (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(180) NOT NULL,
    slug VARCHAR(180) NOT NULL UNIQUE,
    domain VARCHAR(255),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS license_keys (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE,
    label VARCHAR(180) NOT NULL,
    project_id BIGINT NOT NULL REFERENCES license_projects(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'active',
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_by VARCHAR(120),
    notes TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_license_keys_project_status ON license_keys(project_id, status);
CREATE INDEX IF NOT EXISTS idx_license_keys_expires_at ON license_keys(expires_at);
CREATE INDEX IF NOT EXISTS idx_license_keys_last_used_at ON license_keys(last_used_at);

CREATE TABLE IF NOT EXISTS license_audit_log (
    id BIGSERIAL PRIMARY KEY,
    license_id BIGINT NOT NULL REFERENCES license_keys(id) ON DELETE CASCADE,
    action VARCHAR(64) NOT NULL,
    status_before VARCHAR(24),
    status_after VARCHAR(24),
    actor VARCHAR(120),
    ip INET,
    user_agent TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_license_audit_license_created_at ON license_audit_log(license_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_license_audit_action_created_at ON license_audit_log(action, created_at DESC);
