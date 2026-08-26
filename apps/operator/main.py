from __future__ import annotations

import html
import os
from typing import Any

from fastapi import FastAPI
from fastapi.responses import Response

from brain.cognitive_organism import AgencyTier, CognitiveOrganism, GlobalWorkspaceItem
from brain.economic_runtime import EconomicRuntime, InMemoryEconomicStore

app = FastAPI(title="Brain Economic Operator", version="0.2.0")
economic = EconomicRuntime(InMemoryEconomicStore())
organism = CognitiveOrganism()


def _configure_from_env() -> None:
    global economic
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return
    try:
        from brain.adapters.economic_store import PostgresEconomicStore
    except ImportError:
        return
    economic = EconomicRuntime(PostgresEconomicStore(dsn))


_configure_from_env()


def _seed_organism_operator_state() -> None:
    if organism.self_model.current is not None:
        return
    workspace_item = GlobalWorkspaceItem(
        item_type="operator_focus",
        title="Persistence and cockpit verification",
        content="The operator cockpit is focused on durable state, approvals and safe autonomy boundaries.",
        source_refs=["operator:cognitive-organism-persistence-cockpit-v1"],
        salience=0.82,
        novelty=0.55,
        urgency=0.65,
        risk=0.15,
        goal_pressure=0.72,
    )
    organism.admit_workspace_item(workspace_item)
    organism.curiosity.generate(
        "operator_gap",
        ["operator:cognitive-organism-persistence-cockpit-v1"],
        "What production state is missing before higher autonomy is safe?",
        expected_value=0.8,
        uncertainty=0.62,
        falsification_condition="Do not advance autonomy until persistence replay and approval logs survive restart.",
    )
    organism.agency.propose(
        action_type="operator_review",
        proposal="Review persistence checkpoint and approval queue before enabling live source execution.",
        tier=AgencyTier.TIER_3_RECOMMEND,
        source_refs=["operator:cognitive-organism-persistence-cockpit-v1"],
    )
    organism.update_self_state(
        current_focus_summary="Persistence-backed organism cockpit is active",
        belief_count=1,
        event_count=1,
        prediction_count=1,
        opportunity_count=0,
        uncertainty_load=0.35,
        contradiction_load=0.1,
        curiosity_pressure=0.62,
        revenue_pressure=0.55,
        risk_pressure=0.25,
        memory_pressure=0.28,
        action_backlog_pressure=0.35,
        source_event_ids=["operator:cognitive-organism-persistence-cockpit-v1"],
    )


# Shared design tokens for every operator cockpit page. Both cockpit routes
# previously carried their own near-duplicate <style> block with drifting
# colors; centralizing them keeps the two pages visually consistent and
# means a palette change only happens in one place.
_COCKPIT_STYLE = """
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;background:#0b0f14;color:#edf2f7}
main{max-width:1160px;margin:40px auto;padding:0 20px 56px}
h1{font-size:30px;margin:0 0 6px;letter-spacing:-.02em}
p{color:#9aa7b4;line-height:1.5;margin:0 0 20px}
.crumb{display:flex;gap:8px;align-items:center;font-size:13px;color:#5f6d7c;margin-bottom:18px}
.crumb a{color:#9cc9ff;text-decoration:none}
.crumb a:hover{text-decoration:underline}
.crumb .here{color:#edf2f7;font-weight:600}
section.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
article{background:#141b24;border:1px solid #263241;border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:10px}
article strong{font-size:12px;letter-spacing:.08em;color:#9fb0c3}
article span{font-size:30px;font-weight:600}
section.panel{margin-top:18px;background:#101925;border:1px solid #263241;border-radius:10px;padding:18px}
section.panel strong{display:block;margin-bottom:8px;color:#dbeafe}
section.panel ul{margin:0;padding-left:20px}
section.panel li{color:#a7b4c2}
nav.links{margin-top:24px;display:flex;gap:16px;flex-wrap:wrap}
nav.links a{color:#9cc9ff;text-decoration:none;font-size:14px}
nav.links a:hover{text-decoration:underline}
@media (max-width:640px){section.cards{grid-template-columns:repeat(2,1fr)}article span{font-size:24px}}
"""


def _cockpit_cards(rows: list[tuple[str, Any]]) -> str:
    return "".join(
        f"<article><strong>{html.escape(str(label))}</strong><span>{html.escape(str(value))}</span></article>"
        for label, value in rows
    )


def _cockpit_page(
    *,
    title: str,
    active: str,
    lead: str,
    cards_html: str,
    panels_html: str = "",
    nav_links: list[tuple[str, str]],
    refresh_seconds: int = 20,
) -> Response:
    """Render an operator cockpit page with shared layout, a breadcrumb showing
    which cockpit is active, and a no-JS meta-refresh so the numbers stay
    current without requiring the operator to manually reload."""
    crumb = " · ".join(
        f'<span class="here">{html.escape(label)}</span>' if label == active else f'<a href="{href}">{html.escape(label)}</a>'
        for label, href in [("Economic", "/operator/ui"), ("Organism", "/operator/organism/ui")]
    )
    links = "".join(f'<a href="{href}">{html.escape(label)}</a>' for label, href in nav_links)
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="{refresh_seconds}">
<title>{html.escape(title)}</title>
<style>{_COCKPIT_STYLE}</style></head>
<body><main>
<nav class="crumb">{crumb}</nav>
<h1>{html.escape(title)}</h1>
<p>{lead}</p>
<section class="cards">{cards_html}</section>
{panels_html}
<nav class="links">{links}</nav>
</main></body></html>"""
    return Response(content=body, media_type="text/html", headers={"Cache-Control": "no-store"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "surface": "economic-operator"}


@app.get("/operator")
def operator_snapshot() -> dict[str, Any]:
    return economic.operator_snapshot()


@app.get("/operator/pressure")
def pressure_map() -> list[dict[str, Any]]:
    result = []
    for pressure in economic.store.list("pressure"):
        result.append(
            {
                "id": str(pressure.id),
                "entity_id": str(pressure.entity_id),
                "kind": str(pressure.kind),
                "magnitude": pressure.magnitude,
                "effective_magnitude": economic.pressure_effective_magnitude(pressure),
                "confidence": pressure.confidence,
                "state": pressure.metadata.get("state", "hypothesized"),
                "valid_until": pressure.valid_until.isoformat() if pressure.valid_until else None,
            }
        )
    return result


@app.get("/operator/money-paths")
def money_paths() -> list[dict[str, Any]]:
    return [
        {
            "id": str(path.id),
            "verb": str(path.verb),
            "payment_model": str(path.payment_model),
            "buyer_entity_id": str(path.buyer_entity_id) if path.buyer_entity_id else None,
            "expected_gross_value": path.expected_gross_value,
            "expected_net_value": path.expected_net_value,
            "time_to_cash_days": path.time_to_cash_days,
            "conversion_probability": path.conversion_probability,
            "fee_protection_required": path.fee_protection_required,
            "state": path.metadata.get("state", "generated"),
        }
        for path in economic.store.list("money_path")
    ]


@app.get("/operator/counterparties")
def counterparties() -> list[dict[str, Any]]:
    return [
        {
            "id": str(profile.id),
            "entity_id": str(profile.entity_id),
            "roles": sorted(str(role) for role in profile.roles),
            "budget_estimate": profile.budget_estimate,
            "trust": profile.trust,
            "reachability": profile.reachability,
            "decision_authority": profile.decision_authority,
            "state": profile.metadata.get("state", "discovered"),
        }
        for profile in economic.store.list("counterparty")
    ]


@app.get("/operator/transactions")
def transactions() -> list[dict[str, Any]]:
    controls = economic.store.list("fee_control")
    return [
        {
            "id": str(transaction.id),
            "opportunity_id": str(transaction.opportunity_id),
            "status": transaction.status,
            "expected_revenue": transaction.expected_revenue,
            "expected_profit": transaction.expected_profit,
            "capital_at_risk": transaction.capital_at_risk,
            "operator_approval": transaction.metadata.get("approval", "pending"),
            "fee_controlled": any(
                control.transaction_id == transaction.id
                and control.sufficient(fee_sensitive=transaction.expected_revenue > 0)
                for control in controls
            ),
        }
        for transaction in economic.store.list("transaction")
    ]


@app.get("/operator/sources")
def sources() -> list[dict[str, Any]]:
    return [
        {
            "id": str(source.id),
            "source_key": source.source_key,
            "plane": str(source.plane),
            "jurisdiction": source.jurisdiction,
            "status": source.status,
            "reliability": source.reliability,
            "roi": source.roi,
        }
        for source in economic.store.list("source_plane")
    ]


@app.get("/operator/organism")
def organism_operator_snapshot() -> dict[str, Any]:
    _seed_organism_operator_state()
    return organism.cockpit()


@app.get("/operator/ui")
def operator_ui() -> Response:
    snapshot = economic.operator_snapshot()
    cards = _cockpit_cards(
        [
            ("ACT NOW", len(snapshot["act_now"])),
            ("VERIFY FIRST", len(snapshot["verify_first"])),
            ("WATCH", len(snapshot["watch"])),
            ("SUPPRESSED", snapshot["suppressed_count"]),
            ("ACTIVE PRESSURES", snapshot["active_pressures"]),
            ("QUALIFIED MONEY PATHS", snapshot["qualified_money_paths"]),
            ("ACTIVE SOURCES", snapshot["active_sources"]),
            ("TRANSACTIONS", len(snapshot["transactions"])),
            ("COMPOUNDING ASSETS", len(snapshot["compounding_assets"])),
        ]
    )
    return _cockpit_page(
        title="Brain Economic Operator",
        active="Economic",
        lead="Attention, pressure, money paths, transactions, source rights/ROI and compounding state.",
        cards_html=cards,
        nav_links=[
            ("JSON snapshot", "/operator"),
            ("Pressure map", "/operator/pressure"),
            ("Money paths", "/operator/money-paths"),
            ("Counterparties", "/operator/counterparties"),
            ("Transactions", "/operator/transactions"),
            ("Sources", "/operator/sources"),
        ],
    )


@app.get("/operator/organism/ui")
def organism_operator_ui() -> Response:
    _seed_organism_operator_state()
    snapshot = organism.cockpit()
    self_state = snapshot.get("self_state") or {}
    cards = _cockpit_cards(
        [
            ("FOCUS ITEMS", len(snapshot["conscious_focus"]["active_focus"])),
            ("CURIOSITY", len(snapshot["curiosity_queue"])),
            ("ORIGINAL IDEAS", len(snapshot["original_ideas"])),
            ("DREAM INSIGHTS", len(snapshot["dream_insights"])),
            ("DEBATES", len(snapshot["internal_debates"])),
            ("QUARANTINE", len(snapshot["immune_quarantine"])),
            ("ACTIONS", len(snapshot["proposed_actions"])),
            ("DEVELOPMENT EVENTS", len(snapshot["development_timeline"])),
        ]
    )
    focus = html.escape(str(self_state.get("focus", "no self-state yet")))
    boundary = html.escape(str(snapshot["autonomy_boundary"]))
    curiosity = "".join(f"<li>{html.escape(item)}</li>" for item in snapshot["curiosity_queue"])
    actions = "".join(f"<li>{html.escape(item)}</li>" for item in snapshot["proposed_actions"])
    panels = f"""
<section class="panel"><strong>Current focus</strong><p>{focus}</p></section>
<section class="panel"><strong>Autonomy boundary</strong><p>{boundary}</p></section>
<section class="panel"><strong>Curiosity queue</strong><ul>{curiosity}</ul></section>
<section class="panel"><strong>Proposed actions</strong><ul>{actions}</ul></section>"""
    return _cockpit_page(
        title="Brain Organism Operator",
        active="Organism",
        lead="Functional consciousness proxy cockpit. This is governed cognition, not a literal consciousness claim.",
        cards_html=cards,
        panels_html=panels,
        nav_links=[
            ("JSON organism snapshot", "/operator/organism"),
            ("Economic cockpit", "/operator/ui"),
        ],
    )
