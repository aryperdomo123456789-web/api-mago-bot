BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rate_limit_buckets (
    id BIGSERIAL PRIMARY KEY,
    namespace VARCHAR(80) NOT NULL,
    subject VARCHAR(180) NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    count BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_rate_limit_bucket_window UNIQUE (namespace, subject, window_start)
);
CREATE INDEX IF NOT EXISTS idx_rate_limit_bucket_lookup ON rate_limit_buckets(namespace, subject, window_start);

CREATE TABLE IF NOT EXISTS provider_circuit_states (
    id BIGSERIAL PRIMARY KEY,
    provider_type VARCHAR(32) NOT NULL,
    resource_key VARCHAR(180) NOT NULL,
    state VARCHAR(16) NOT NULL DEFAULT 'closed',
    failure_count BIGINT NOT NULL DEFAULT 0,
    opened_until TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_provider_circuit_resource UNIQUE (provider_type, resource_key)
);
CREATE INDEX IF NOT EXISTS idx_provider_circuit_state ON provider_circuit_states(state, opened_until);

INSERT INTO schema_migrations (version)
VALUES ('0006_resilience_limits')
ON CONFLICT (version) DO NOTHING;

COMMIT;
