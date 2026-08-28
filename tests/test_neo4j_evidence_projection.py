from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from brain.adapters.neo4j_projection import Neo4jConfig, Neo4jProjection
from brain.domain import Edge, Evidence, Node


TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
NODE_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
NODE_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
EDGE = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
EVID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


class _Result:
    def consume(self):
        return self


class _Session:
    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def run(self, query, **params):
        self.calls.append((" ".join(query.split()), params))
        return _Result()


class _Driver:
    def __init__(self):
        self.calls = []
        self.closed = False

    def session(self, *, database):
        self.calls.append(("database", database))
        return _Session(self.calls)

    def verify_connectivity(self):
        return None

    def close(self):
        self.closed = True


def _projection() -> tuple[Neo4jProjection, _Driver]:
    driver = _Driver()
    return (
        Neo4jProjection(
            Neo4jConfig("neo4j://example", "neo4j", "secret"),
            driver=driver,
        ),
        driver,
    )


def test_upsert_evidence_is_tenant_scoped():
    projection, driver = _projection()
    evidence = Evidence(
        id=EVID,
        claim="market expanding",
        source_id="src-1",
        reliability=0.8,
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    projection.upsert_evidence(evidence, scope=TENANT_A)
    query, params = next(
        (q, p)
        for q, p in driver.calls
        if isinstance(q, str) and "BrainEvidence" in q and "MERGE" in q
    )
    assert params["projection_id"] == f"{TENANT_A}:{EVID}"
    assert params["props"]["tenant_scope"] == str(TENANT_A)
    assert params["props"]["claim"] == "market expanding"
    assert params["props"]["reliability"] == 0.8


def test_upsert_edge_links_evidence_via_justifies():
    projection, driver = _projection()
    edge = Edge(
        id=EDGE,
        source=NODE_A,
        target=NODE_B,
        relation="supports",
        weight=0.7,
        confidence=0.8,
        evidence_ids={EVID},
        updated_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    projection.upsert_edge(edge, scope=TENANT_A)
    queries = [c for c in driver.calls if isinstance(c[0], str) and c[0] != "database"]
    assert any("evidence_count" in str(p) for _, p in queries)
    justifies = [p for q, p in queries if "JUSTIFIES" in q and "endpoint" in q]
    assert justifies
    assert justifies[0]["edge_projection_id"] == f"{TENANT_A}:{EDGE}"
    assert justifies[0]["evidence_projection_id"] == f"{TENANT_A}:{EVID}"


def test_rebuild_returns_evidence_count():
    projection, driver = _projection()
    evidence = Evidence(
        id=EVID,
        claim="x",
        source_id="s",
        reliability=0.5,
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    result = projection.rebuild([], [], scope=TENANT_A, evidence=[evidence])
    assert result["evidence"] == 1
    assert result["nodes"] == 0
    assert result["edges"] == 0
    assert any(
        isinstance(q, str) and "BrainEvidence" in q and "DETACH DELETE" in q
        for q, _p in ((c[0], c[1] if len(c) > 1 else {}) for c in driver.calls if isinstance(c, tuple))
    )
