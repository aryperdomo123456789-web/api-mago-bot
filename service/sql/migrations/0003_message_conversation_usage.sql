BEGIN;

ALTER TABLE outbound_messages
    ADD COLUMN IF NOT EXISTS conversation_id BIGINT REFERENCES conversations(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_outbound_messages_conversation
    ON outbound_messages(conversation_id, created_at);

ALTER TABLE conversation_events
    ADD COLUMN IF NOT EXISTS outbound_message_id BIGINT REFERENCES outbound_messages(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_conversation_events_outbound_message
    ON conversation_events(outbound_message_id);

CREATE TABLE IF NOT EXISTS usage_ledger_entries (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    tenant_id BIGINT NOT NULL REFERENCES platform_tenants(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    message_id BIGINT REFERENCES outbound_messages(id) ON DELETE SET NULL,
    metric VARCHAR(80) NOT NULL,
    units BIGINT NOT NULL DEFAULT 1,
    provider_type VARCHAR(32),
    source_type VARCHAR(80) NOT NULL,
    source_id VARCHAR(180) NOT NULL,
    cost_micros BIGINT NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_usage_ledger_source UNIQUE(tenant_id, source_type, source_id, metric),
    CONSTRAINT ck_usage_ledger_units_positive CHECK (units > 0),
    CONSTRAINT ck_usage_ledger_cost_nonnegative CHECK (cost_micros >= 0)
);

CREATE INDEX IF NOT EXISTS idx_usage_ledger_tenant_created
    ON usage_ledger_entries(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_ledger_tenant_metric_created
    ON usage_ledger_entries(tenant_id, metric, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_ledger_message
    ON usage_ledger_entries(message_id);

CREATE OR REPLACE FUNCTION forbid_usage_ledger_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'usage_ledger_entries is append-only';
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_usage_ledger_append_only'
    ) THEN
        CREATE TRIGGER trg_usage_ledger_append_only
        BEFORE UPDATE OR DELETE ON usage_ledger_entries
        FOR EACH ROW EXECUTE FUNCTION forbid_usage_ledger_mutation();
    END IF;
END;
$$;

INSERT INTO schema_migrations(version)
VALUES ('0003_message_conversation_usage')
ON CONFLICT (version) DO NOTHING;

COMMIT;
