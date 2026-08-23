from __future__ import annotations

import html
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from brain.adapters.developmental_store import InMemoryDevelopmentalStore
from brain.developmental.runtime import DevelopmentalRuntime
from brain.economic_runtime import EconomicRuntime, InMemoryEconomicStore
from brain.security import ApiKeyAuthenticator, SecurityConfig

_security = SecurityConfig.from_env()
_authenticator = ApiKeyAuthenticator(_security)
app = FastAPI(title="Brain Operator", version="0.2.0")
economic = EconomicRuntime(InMemoryEconomicStore())
development = DevelopmentalRuntime(InMemoryDevelopmentalStore())


@app.middleware("http")
async def production_authentication(request: Request, call_next):
    if request.url.path != "/health" and not _authenticator.authorized(
        authorization=request.headers.get("authorization"),
        x_api_key=request.headers.get("x-brain-api-key"),
    ):
        return JSONResponse(status_code=401, content={"detail": "brain_authentication_required"})
    return await call_next(request)


def _configure_from_env() -> None:
    global economic, development
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return
    from brain.adapters.developmental_store import PostgresDevelopmentalStore
    from brain.adapters.economic_store import PostgresEconomicStore

    economic = EconomicRuntime(PostgresEconomicStore(dsn))
    development = DevelopmentalRuntime(PostgresDevelopmentalStore(dsn))


_configure_from_env()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "surface": "brain-operator"}


@app.get("/operator")
def operator_snapshot() -> dict[str, Any]:
    snapshot = economic.operator_snapshot()
    snapshot["development"] = developmental_snapshot()
    return snapshot


@app.get("/operator/development")
def developmental_snapshot() -> dict[str, Any]:
    kinds = [
        "prediction_error",
        "development_pressure",
        "workspace_coalition",
        "workspace_suppression",
        "workspace_broadcast",
        "consolidation_run",
        "dream_rewire_proposal",
        "immune_alert",
        "quarantine",
        "memory_compression",
    ]
    return {
        "counts": {kind: len(development.store.list(kind)) for kind in kinds},
        "recent_pressures": development.store.list("development_pressure")[-20:],
        "recent_immune_alerts": development.store.list("immune_alert")[-20:],
        "recent_workspace_broadcasts": development.store.list("workspace_broadcast")[-20:],
        "recent_quarantines": development.store.list("quarantine")[-20:],
        "scores": list(getattr(development.store, "scores", []))[-20:],
        "transitions": list(getattr(development.store, "transitions", []))[-20:],
    }


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


@app.get("/operator/ui", response_class=HTMLResponse)
def operator_ui() -> str:
    snapshot = economic.operator_snapshot()
    dev = developmental_snapshot()
    rows = [
        ("ACT NOW", len(snapshot["act_now"])),
        ("VERIFY FIRST", len(snapshot["verify_first"])),
        ("WATCH", len(snapshot["watch"])),
        ("SUPPRESSED", snapshot["suppressed_count"]),
        ("ACTIVE PRESSURES", snapshot["active_pressures"]),
        ("QUALIFIED MONEY PATHS", snapshot["qualified_money_paths"]),
        ("ACTIVE SOURCES", snapshot["active_sources"]),
        ("TRANSACTIONS", len(snapshot["transactions"])),
        ("DEVELOPMENT PRESSURES", dev["counts"]["development_pressure"]),
        ("IMMUNE ALERTS", dev["counts"]["immune_alert"]),
        ("WORKSPACE BROADCASTS", dev["counts"]["workspace_broadcast"]),
        ("QUARANTINES", dev["counts"]["quarantine"]),
    ]
    cards = "".join(
        f"<article><strong>{html.escape(label)}</strong><span>{value}</span></article>"
        for label, value in rows
    )
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Brain Operator</title>
<style>
body{{font-family:system-ui;margin:0;background:#0b0f14;color:#edf2f7}}
main{{max-width:1100px;margin:40px auto;padding:0 20px}}
h1{{font-size:30px}}p{{color:#9aa7b4}}
section{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}}
article{{background:#141b24;border:1px solid #263241;border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:10px}}
article strong{{font-size:12px;letter-spacing:.08em;color:#9fb0c3}}article span{{font-size:30px}}
nav{{margin-top:24px;display:flex;gap:16px;flex-wrap:wrap}}a{{color:#9cc9ff}}
</style></head><body><main><h1>Brain Operator</h1>
<p>Economic cognition plus developmental pressure, global workspace, immune defense and consolidation state.</p>
<section>{cards}</section><nav>
<a href='/operator'>JSON snapshot</a><a href='/operator/development'>Development</a>
<a href='/operator/pressure'>Pressure map</a><a href='/operator/money-paths'>Money paths</a>
<a href='/operator/counterparties'>Counterparties</a><a href='/operator/transactions'>Transactions</a>
<a href='/operator/sources'>Sources</a>
</nav></main></body></html>"""
