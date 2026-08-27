"""Idempotent production baseline for the Brain Observatory.

This pack contains only internal system facts, explicitly-labelled architecture
hypotheses, open questions, and validation predictions. It is not external
intelligence and must never be presented as such.

The script is inert unless BRAIN_OBSERVATORY_SEED_PACK is exactly
``observatory-production-seed-v1``. Stable UUID5 identifiers make every write
idempotent; re-running the pack cannot multiply records.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

import psycopg
from psycopg.types.json import Jsonb

SEED_PACK = "observatory-production-seed-v1"
SEED_NAMESPACE = f"brain:{SEED_PACK}"


def sid(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"{SEED_NAMESPACE}:{name}")


@dataclass(frozen=True)
class BeliefSeed:
    key: str
    statement: str
    confidence: float
    state: str
    unknowns: tuple[str, ...]


BELIEFS = (
    BeliefSeed(
        "transport",
        "Production Observatory transport reaches all 18 canonical Brain read surfaces.",
        0.92,
        "established",
        (
            "Does every successful read surface render its full semantic state in the "
            "current Observatory UI?",
        ),
    ),
    BeliefSeed(
        "durability",
        "Brain cognition should persist through PostgreSQL so process restarts do not erase learned state.",
        0.79,
        "provisional",
        (
            "Which cognition projections still depend on process-local state?",
            "What dedicated-worker capacity is required before moving beyond inline cognition?",
        ),
    ),
    BeliefSeed(
        "source-quality",
        "Verified source ingestion is the next major data-quality improvement after the production baseline is stable.",
        0.76,
        "provisional",
        (
            "Which approved source classes deliver the highest information gain per unit cost?",
            "What freshness SLA should each source class have?",
        ),
    ),
    BeliefSeed(
        "worker-required",
        "A dedicated worker is strictly required for Brain cognition to progress.",
        0.50,
        "contested",
        (
            "Does lease-controlled inline cognition provide equivalent continuity under "
            "current production load?",
        ),
    ),
    BeliefSeed(
        "tenant-release",
        "Tenant-RLS migrations 019-022 must remain release-gated until split identities and legacy-data strategy are verified.",
        0.91,
        "established",
        (
            "What evidence will prove the production role split and Strategy A quarantine "
            "are ready for release?",
        ),
    ),
)

SOURCES = (
    ("production-runtime", "Brain production runtime", 0.95),
    ("repository-contract", "Brain repository contract", 0.92),
    ("observatory-runtime", "Brain Observatory runtime", 0.90),
    ("deployment-control", "Brain deployment controls", 0.94),
    ("architecture-review", "Brain architecture review", 0.82),
)

# belief key, evidence key, source key, claim, reliability, relation, evidence class
EVIDENCE = (
    (
        "transport",
        "transport-live",
        "observatory-runtime",
        "Repeated production polling has returned HTTP 200 on all 18 canonical read surfaces.",
        0.96,
        "supports",
        "verified_internal_fact",
    ),
    (
        "durability",
        "durability-db",
        "repository-contract",
        "PostgreSQL is the authoritative durable state store for production cognition and read models.",
        0.94,
        "supports",
        "verified_internal_fact",
    ),
    (
        "source-quality",
        "source-next",
        "architecture-review",
        "A populated baseline without verified source ingestion improves observability but does not create fresh external intelligence.",
        0.88,
        "supports",
        "architecture_inference",
    ),
    (
        "worker-required",
        "worker-preferred",
        "repository-contract",
        "The two-process API plus worker architecture remains the preferred steady-state production shape.",
        0.82,
        "supports",
        "architecture_fact",
    ),
    (
        "worker-required",
        "inline-counterexample",
        "production-runtime",
        "Lease-controlled inline cognition can progress when no dedicated worker owns the cognition lease.",
        0.93,
        "contradicts",
        "verified_internal_fact",
    ),
    (
        "tenant-release",
        "tenant-gate",
        "deployment-control",
        "Production ordinary deploys are intentionally pinned through migration 018 while 019-022 require explicit tenant release authorization.",
        0.97,
        "supports",
        "verified_internal_fact",
    ),
)

NODES = (
    ("vercel-observatory", "service", "Vercel Observatory"),
    ("deployment-identity", "identity", "Vercel deployment identity"),
    ("railway-api", "service", "Railway brain-api-live"),
    ("postgres", "database", "Production PostgreSQL"),
    ("inline-cognition", "runtime", "Lease-controlled inline cognition"),
    ("tenant-release-gate", "control", "Tenant release gate"),
    ("verified-source-ingestion", "pipeline", "Verified source ingestion"),
)

# key, source node, target node, relation, weight, confidence, evidence key
EDGES = (
    (
        "obs-polls-api",
        "vercel-observatory",
        "railway-api",
        "polls",
        0.96,
        0.96,
        "transport-live",
    ),
    (
        "identity-auth-api",
        "deployment-identity",
        "railway-api",
        "authenticates_to",
        0.94,
        0.94,
        "transport-live",
    ),
    ("api-db", "railway-api", "postgres", "reads_writes", 0.95, 0.95, "durability-db"),
    (
        "inline-db",
        "inline-cognition",
        "postgres",
        "persists_to",
        0.88,
        0.88,
        "durability-db",
    ),
    (
        "tenant-gate-api",
        "tenant-release-gate",
        "railway-api",
        "constrains",
        0.97,
        0.97,
        "tenant-gate",
    ),
    (
        "sources-feed-cognition",
        "verified-source-ingestion",
        "inline-cognition",
        "feeds",
        0.72,
        0.72,
        "source-next",
    ),
)

PREDICTIONS = (
    (
        "cycle-advances",
        "If a baseline stimulus enters the durable sensory inbox, cycle.completed count should increase without an API restart.",
        1.0,
        0.92,
        "durability",
        6 * 3600,
    ),
    (
        "projection-visible",
        "If PostgreSQL projection refresh is functioning, seeded beliefs and graph edges should become visible within one Observatory polling interval.",
        1.0,
        0.94,
        "transport",
        6 * 3600,
    ),
    (
        "source-volume",
        "If verified source ingestion remains unconfigured, system cognition can run while fresh external intelligence volume remains limited.",
        1.0,
        0.86,
        "source-quality",
        24 * 3600,
    ),
)

STIMULI = (
    (
        "stimulus-transport",
        "Production transport baseline is healthy across all canonical Observatory reads.",
        "Production transport is currently healthy across the canonical Observatory read surface.",
        "observatory-runtime",
        0.94,
        0.55,
        0.55,
    ),
    (
        "stimulus-persistence",
        "Inspect durable cognition continuity and projection freshness after deployment.",
        "Durable cognition should survive process replacement without returning the Observatory to an empty state.",
        "production-runtime",
        0.91,
        0.72,
        0.68,
    ),
    (
        "stimulus-worker",
        "Evaluate inline cognition against the preferred dedicated-worker architecture.",
        "Inline cognition is a valid continuity fallback, while a dedicated worker remains the preferred steady-state architecture.",
        "architecture-review",
        0.84,
        0.78,
        0.62,
    ),
    (
        "stimulus-sources",
        "Prioritize verified source ingestion after the production cognition baseline is proven stable.",
        "Fresh verified source ingestion should be prioritized over additional cosmetic dashboard instrumentation.",
        "repository-contract",
        0.89,
        0.82,
        0.64,
    ),
)


def _required_tables_present(conn: psycopg.Connection) -> bool:
    names = (
        "brain_events",
        "beliefs",
        "evidence",
        "belief_evidence",
        "graph_nodes",
        "graph_edges",
        "predictions",
        "sensory_inbox",
    )
    row = conn.execute(
        "select count(*) from unnest(%s::text[]) n "
        "where to_regclass('public.' || n) is not null",
        (list(names),),
    ).fetchone()
    return bool(row and int(row[0]) == len(names))


def _column_exists(conn: psycopg.Connection, table: str, column: str) -> bool:
    row = conn.execute(
        """
        select exists (
          select 1
          from information_schema.columns
          where table_schema = 'public' and table_name = %s and column_name = %s
        )
        """,
        (table, column),
    ).fetchone()
    return bool(row and row[0])


def _upsert_system_source(
    conn: psycopg.Connection,
    *,
    key: str,
    name: str,
    trust: float,
) -> int:
    """Upsert a global seed source across both pre-020 and tenant-aware schemas."""

    metadata = Jsonb(
        {"seed_pack": SEED_PACK, "source_class": "internal_system_evidence"}
    )
    values = (sid(f"source:{key}"), f"seed:{key}", name, trust, trust, metadata)
    if _column_exists(conn, "sources", "tenant_id"):
        # Migration 020 replaces sources_key_key with a partial unique index for
        # system rows. The matching predicate is part of PostgreSQL's conflict
        # target contract and prevents collisions with a tenant-owned source using
        # the same natural key.
        result = conn.execute(
            """
            insert into public.sources (
              id, key, name, authority_score, historical_utility, metadata, tenant_id
            ) values (%s,%s,%s,%s,%s,%s,null)
            on conflict (key) where tenant_id is null do update set
              name=excluded.name,
              authority_score=excluded.authority_score,
              historical_utility=excluded.historical_utility,
              metadata=public.sources.metadata || excluded.metadata
            """,
            values,
        )
    else:
        result = conn.execute(
            """
            insert into public.sources (id, key, name, authority_score, historical_utility, metadata)
            values (%s,%s,%s,%s,%s,%s)
            on conflict (key) do update set
              name=excluded.name,
              authority_score=excluded.authority_score,
              historical_utility=excluded.historical_utility,
              metadata=public.sources.metadata || excluded.metadata
            """,
            values,
        )
    return int(result.rowcount)


def apply_seed(conn: psycopg.Connection) -> dict[str, int]:
    if not _required_tables_present(conn):
        raise RuntimeError("observatory_seed_requires_migrations_001_through_018")

    now = datetime.now(UTC)
    counts = {
        "sources": 0,
        "beliefs": 0,
        "evidence": 0,
        "edges": 0,
        "predictions": 0,
        "signals": 0,
        "inbox": 0,
    }

    for key, name, trust in SOURCES:
        counts["sources"] += _upsert_system_source(
            conn,
            key=key,
            name=name,
            trust=trust,
        )

    for belief in BELIEFS:
        result = conn.execute(
            """
            insert into public.beliefs (id, statement, confidence, state, unknowns, version, updated_at)
            values (%s,%s,%s,%s,%s,1,%s)
            on conflict (id) do update set
              statement=excluded.statement,
              confidence=excluded.confidence,
              state=excluded.state,
              unknowns=excluded.unknowns,
              updated_at=excluded.updated_at
            where public.beliefs.version = 1
            """,
            (
                sid(f"belief:{belief.key}"),
                belief.statement,
                belief.confidence,
                belief.state,
                Jsonb(list(belief.unknowns)),
                now,
            ),
        )
        counts["beliefs"] += result.rowcount

    evidence_ids: dict[str, UUID] = {}
    for belief_key, evidence_key, source_key, claim, reliability, relation, evidence_class in EVIDENCE:
        evidence_id = sid(f"evidence:{evidence_key}")
        evidence_ids[evidence_key] = evidence_id
        result = conn.execute(
            """
            insert into public.evidence (id, observation_id, claim, reliability, stance, created_at, metadata)
            values (%s,null,%s,%s,'neutral',%s,%s)
            on conflict (id) do update set
              claim=excluded.claim,
              reliability=excluded.reliability,
              metadata=excluded.metadata
            """,
            (
                evidence_id,
                claim,
                reliability,
                now,
                Jsonb(
                    {
                        "source_id": f"seed:{source_key}",
                        "seed_pack": SEED_PACK,
                        "evidence_class": evidence_class,
                    }
                ),
            ),
        )
        counts["evidence"] += result.rowcount
        conn.execute(
            """
            insert into public.belief_evidence (belief_id, evidence_id, relation)
            values (%s,%s,%s)
            on conflict (belief_id, evidence_id) do update set relation=excluded.relation
            """,
            (sid(f"belief:{belief_key}"), evidence_id, relation),
        )

    for key, kind, label in NODES:
        conn.execute(
            """
            insert into public.graph_nodes (id, kind, node_key, properties)
            values (%s,%s,%s,%s)
            on conflict (id) do update set
              kind=excluded.kind,
              node_key=excluded.node_key,
              properties=excluded.properties
            """,
            (
                sid(f"node:{key}"),
                kind,
                f"seed:{key}",
                Jsonb({"label": label, "seed_pack": SEED_PACK}),
            ),
        )

    for key, source_key, target_key, relation, weight, confidence, evidence_key in EDGES:
        result = conn.execute(
            """
            insert into public.graph_edges (
              id, source_id, target_id, relation, weight, confidence, evidence_ids, updated_at
            ) values (%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (id) do update set
              source_id=excluded.source_id,
              target_id=excluded.target_id,
              relation=excluded.relation,
              weight=excluded.weight,
              confidence=excluded.confidence,
              evidence_ids=excluded.evidence_ids,
              updated_at=excluded.updated_at
            """,
            (
                sid(f"edge:{key}"),
                sid(f"node:{source_key}"),
                sid(f"node:{target_key}"),
                relation,
                weight,
                confidence,
                [evidence_ids[evidence_key]],
                now,
            ),
        )
        counts["edges"] += result.rowcount

    for key, statement, expected_value, confidence, belief_key, horizon_seconds in PREDICTIONS:
        result = conn.execute(
            """
            insert into public.predictions (
              id, statement, expected_value, confidence, horizon_seconds, belief_id,
              action_id, edge_ids, source_keys, status, created_at, resolve_by, metadata
            ) values (%s,%s,%s,%s,%s,%s,null,'{}','{observatory-production-seed-v1}',
                      'open',%s,%s,%s)
            on conflict (id) do update set
              statement=excluded.statement,
              expected_value=excluded.expected_value,
              confidence=excluded.confidence,
              belief_id=excluded.belief_id,
              status=case
                when public.predictions.status='open' then 'open'
                else public.predictions.status
              end,
              metadata=public.predictions.metadata || excluded.metadata
            """,
            (
                sid(f"prediction:{key}"),
                statement,
                expected_value,
                confidence,
                horizon_seconds,
                sid(f"belief:{belief_key}"),
                now,
                now + timedelta(seconds=horizon_seconds),
                Jsonb({"seed_pack": SEED_PACK, "prediction_class": "system_validation"}),
            ),
        )
        counts["predictions"] += result.rowcount

    for key, content, claim, source_key, reliability, novelty, urgency in STIMULI:
        inbox_id = sid(f"inbox:{key}")
        payload = {
            "source_reliability": reliability,
            "supports": True,
            "belief_statement": claim,
            "belief_confidence": 0.62,
            "novelty": novelty,
            "urgency": urgency,
            "commercial_upside": 0.35,
            "contradiction_value": 0.20 if key == "stimulus-worker" else 0.05,
            "uncertainty_reduction": 0.72,
            "noise_probability": 0.04,
            "operator_burden": 0.02,
            "metadata": {
                "seed_pack": SEED_PACK,
                "source_class": "internal_system_evidence",
            },
        }
        result = conn.execute(
            """
            insert into public.sensory_inbox (
              id, source_key, content, claim, payload, status, attempts, available_at, created_at
            ) values (%s,%s,%s,%s,%s,'pending',0,%s,%s)
            on conflict (id) do nothing
            """,
            (inbox_id, f"seed:{source_key}", content, claim, Jsonb(payload), now, now),
        )
        counts["inbox"] += result.rowcount

        event_id = sid(f"event:signal:{key}")
        result = conn.execute(
            """
            insert into public.brain_events (
              id,event_type,aggregate_type,aggregate_id,causation_id,correlation_id,payload,occurred_at
            ) values (%s,'signal.enqueued','sensory_inbox',%s,null,null,%s,%s)
            on conflict (id) do nothing
            """,
            (
                event_id,
                inbox_id,
                Jsonb(
                    {
                        "source_key": f"seed:{source_key}",
                        "content": content,
                        "claim": claim,
                        "payload": payload,
                        "seed_pack": SEED_PACK,
                    }
                ),
                now,
            ),
        )
        counts["signals"] += result.rowcount

    for belief in BELIEFS:
        conn.execute(
            """
            insert into public.brain_events (
              id,event_type,aggregate_type,aggregate_id,causation_id,correlation_id,payload,occurred_at
            ) values (%s,'belief.created','belief',%s,null,null,%s,%s)
            on conflict (id) do nothing
            """,
            (
                sid(f"event:belief:{belief.key}"),
                sid(f"belief:{belief.key}"),
                Jsonb(
                    {
                        "statement": belief.statement,
                        "confidence": belief.confidence,
                        "state": belief.state,
                        "seed_pack": SEED_PACK,
                    }
                ),
                now,
            ),
        )

    if conn.execute("select to_regclass('public.organism_audit_events')").fetchone()[0]:
        conn.execute(
            """
            insert into public.organism_audit_events (
              id,event_type,object_type,object_id,payload,created_at
            ) values (%s,'OBSERVATORY_PRODUCTION_SEED_APPLIED','seed_pack',%s,%s,%s)
            on conflict (id) do nothing
            """,
            (
                sid("audit:applied"),
                SEED_PACK,
                Jsonb({"seed_pack": SEED_PACK, "external_intelligence": False}),
                now,
            ),
        )

    conn.commit()
    return counts


def main() -> int:
    requested = (os.environ.get("BRAIN_OBSERVATORY_SEED_PACK") or "").strip()
    if requested != SEED_PACK:
        print("Observatory production seed disabled; no changes applied.")
        return 0
    # Post-tenant releases run with FORCE RLS. Use the same separately-audited
    # migration identity when it is available so this explicitly operator-enabled
    # system seed can write tenant_id IS NULL control rows. Pre-tenant production
    # remains compatible by falling back to DATABASE_URL.
    dsn = (
        os.environ.get("BRAIN_MIGRATION_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL or BRAIN_MIGRATION_DATABASE_URL is required when Observatory production seed is enabled"
        )
    with psycopg.connect(dsn) as conn:
        counts = apply_seed(conn)
    print(f"Observatory production seed ensured: {SEED_PACK}; writes={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())