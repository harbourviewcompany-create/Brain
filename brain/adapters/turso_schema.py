from __future__ import annotations

TURSO_SCHEMA = """
CREATE TABLE IF NOT EXISTS brain_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    causation_id TEXT,
    correlation_id TEXT,
    payload TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS brain_events_type_idx
    ON brain_events(event_type, occurred_at, id);
CREATE INDEX IF NOT EXISTS brain_events_cursor_idx
    ON brain_events(occurred_at, id);

-- Permanent identity index. IDs remain here after physical event compaction so
-- INSERT OR IGNORE keeps the canonical ledger idempotent across hot + archive.
CREATE TABLE IF NOT EXISTS brain_event_ids (
    id TEXT PRIMARY KEY,
    occurred_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS brain_event_type_counts (
    event_type TEXT PRIMARY KEY,
    event_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS brain_event_segments (
    segment_id TEXT PRIMARY KEY,
    first_occurred_at TEXT NOT NULL,
    first_event_id TEXT NOT NULL,
    last_occurred_at TEXT NOT NULL,
    last_event_id TEXT NOT NULL,
    event_count INTEGER NOT NULL,
    event_types TEXT NOT NULL,
    compression TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    payload BLOB NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS brain_event_segments_cursor_idx
    ON brain_event_segments(last_occurred_at, last_event_id);

CREATE TABLE IF NOT EXISTS projection_checkpoints (
    projection_name TEXT PRIMARY KEY,
    last_event_id TEXT,
    event_count INTEGER NOT NULL,
    state TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brain_telemetry (
    id TEXT PRIMARY KEY,
    telemetry_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS brain_telemetry_expiry_idx ON brain_telemetry(expires_at);

CREATE TABLE IF NOT EXISTS beliefs (
    id TEXT PRIMARY KEY,
    statement TEXT NOT NULL,
    confidence REAL NOT NULL,
    state TEXT NOT NULL,
    unknowns TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    observation_id TEXT,
    claim TEXT NOT NULL,
    reliability REAL NOT NULL,
    stance TEXT NOT NULL DEFAULT 'neutral',
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS belief_evidence (
    belief_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    PRIMARY KEY (belief_id, evidence_id)
);
CREATE TABLE IF NOT EXISTS graph_nodes (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    node_key TEXT NOT NULL,
    properties TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS graph_edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    weight REAL NOT NULL,
    confidence REAL NOT NULL,
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rewire_events (
    id TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    target_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    previous TEXT NOT NULL DEFAULT '{}',
    current TEXT NOT NULL DEFAULT '{}',
    evidence_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS predictions (
    id TEXT PRIMARY KEY,
    statement TEXT NOT NULL,
    expected_value REAL NOT NULL,
    confidence REAL NOT NULL,
    horizon_seconds INTEGER NOT NULL,
    belief_id TEXT,
    action_id TEXT,
    edge_ids TEXT NOT NULL DEFAULT '[]',
    source_keys TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolve_by TEXT,
    resolved_at TEXT,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS attribution_records (
    id TEXT PRIMARY KEY,
    outcome_id TEXT NOT NULL,
    prediction_id TEXT,
    edge_ids TEXT NOT NULL DEFAULT '[]',
    source_keys TEXT NOT NULL DEFAULT '[]',
    reward_score REAL NOT NULL,
    prediction_error REAL NOT NULL,
    edge_deltas TEXT NOT NULL DEFAULT '{}',
    source_deltas TEXT NOT NULL DEFAULT '{}',
    rationale TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    key TEXT UNIQUE,
    authority_score REAL NOT NULL DEFAULT 0.5,
    historical_utility REAL NOT NULL DEFAULT 0.5
);

CREATE TABLE IF NOT EXISTS money_lanes (
    lane_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    opportunity_class TEXT NOT NULL,
    packaged_offer TEXT NOT NULL,
    buyer_type TEXT NOT NULL,
    seller_or_target_type TEXT NOT NULL,
    first_48_hour_action TEXT NOT NULL,
    price_low REAL NOT NULL,
    price_high REAL NOT NULL,
    repeatability REAL NOT NULL,
    fulfillment_difficulty REAL NOT NULL,
    time_to_cash_days REAL NOT NULL,
    automation_readiness TEXT NOT NULL,
    legal_access_risk REAL NOT NULL,
    priority_score REAL NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revenue_source_scores (
    source_id TEXT PRIMARY KEY,
    score REAL NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revenue_execution_actions (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    offer_id TEXT NOT NULL,
    lane_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_contact TEXT NOT NULL,
    proposal TEXT NOT NULL,
    evidence_refs TEXT NOT NULL DEFAULT '[]',
    approval_required INTEGER NOT NULL,
    state TEXT NOT NULL,
    approved_by TEXT,
    manual_proof_ref TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revenue_followups (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    due_at TEXT NOT NULL,
    script TEXT NOT NULL,
    state TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS revenue_outcome_ledger (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    lane_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    outcome_type TEXT NOT NULL,
    revenue REAL NOT NULL,
    reply INTEGER NOT NULL,
    meeting_booked INTEGER NOT NULL,
    paid_conversion INTEGER NOT NULL,
    legal_risk REAL NOT NULL,
    operator_hours REAL NOT NULL,
    lesson TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
