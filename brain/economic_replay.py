from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from .economic import (
    CounterpartyProfile,
    CounterpartyRole,
    EconomicOpportunity,
    OpportunityType,
    PaymentModel,
    PressureType,
    RevenueAttribution,
    Transaction,
)
from .economic_runtime import (
    EconomicRuntime,
    FeeControl,
    InMemoryEconomicStore,
    SourcePlane,
    SourcePlaneType,
    SourceRightsClass,
    SourceRightsProfile,
)


@dataclass(frozen=True, slots=True)
class EconomicReplayResult:
    fixture_id: str
    passed: bool
    deterministic_signature: tuple[Any, ...]
    events: tuple[str, ...]
    assertions: tuple[str, ...]
    operator_snapshot: dict[str, Any]


class EconomicReplayHarness:
    """Deterministic fixture replay for MOD-008 through MOD-015."""

    def run(self, fixture: str | Path | dict[str, Any]) -> EconomicReplayResult:
        data = self._load(fixture)
        runtime = EconomicRuntime(InMemoryEconomicStore())
        events: list[str] = []
        assertions: list[str] = []
        scenario = data["scenario_type"]

        if scenario == "commercial_pipeline":
            self._commercial_pipeline(runtime, data, events, assertions)
        elif scenario == "source_rights":
            self._source_rights(runtime, data, events, assertions)
        elif scenario == "transaction_control":
            self._transaction_control(runtime, data, events, assertions)
        elif scenario == "compounding":
            self._compounding(runtime, data, events, assertions)
        else:
            raise ValueError(f"unknown_economic_fixture:{scenario}")

        snapshot = runtime.operator_snapshot()
        signature = (
            data["fixture_id"],
            tuple(events),
            tuple(assertions),
            tuple(snapshot["act_now"]),
            tuple(snapshot["verify_first"]),
            snapshot["suppressed_count"],
        )
        return EconomicReplayResult(
            fixture_id=data["fixture_id"],
            passed=all(not item.startswith("FAIL:") for item in assertions),
            deterministic_signature=signature,
            events=tuple(events),
            assertions=tuple(assertions),
            operator_snapshot=snapshot,
        )

    def write_report(self, result: EconomicReplayResult, path: str | Path) -> None:
        output = {
            "fixture_id": result.fixture_id,
            "verdict": "GO" if result.passed else "HOLD",
            "events": list(result.events),
            "assertions": list(result.assertions),
            "signature": list(result.deterministic_signature),
            "operator_snapshot": result.operator_snapshot,
        }
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")

    def _commercial_pipeline(
        self,
        runtime: EconomicRuntime,
        data: dict[str, Any],
        events: list[str],
        assertions: list[str],
    ) -> None:
        entity_id = UUID(data["entity_id"])
        evidence_ids = [UUID(v) for v in data["evidence_ids"]]
        pressure = runtime.infer_pressure(
            entity_id,
            PressureType(data["pressure_type"]),
            data["pressure_magnitude"],
            data["pressure_confidence"],
            evidence_ids,
            half_life_days=data.get("half_life_days", 30),
        )
        events.append("pressure.inferred")
        affordance = runtime.generate_affordances(entity_id, [pressure.kind], evidence_ids)[0]
        events.append("affordance.generated")
        buyer_id = UUID(data["buyer_entity_id"])
        profile = CounterpartyProfile(
            entity_id=buyer_id,
            roles={CounterpartyRole.BUYER},
            budget_estimate=data["buyer_budget"],
            trust=0.8,
            reachability=0.9,
            decision_authority=0.9,
            urgency=0.8,
        )
        runtime.upsert_counterparty(profile, verified=True)
        path = runtime.generate_money_path(
            affordance=affordance,
            payment_model=PaymentModel(data["payment_model"]),
            buyer_entity_id=buyer_id,
            gross_value=data["gross_value"],
            net_value=data["net_value"],
            time_to_cash_days=data["time_to_cash_days"],
            conversion_probability=data["conversion_probability"],
            fee_protection_required=data.get("fee_protection_required", False),
        )
        runtime.qualify_money_path(path.id, payer_verified=True)
        events.append("money_path.qualified")
        opportunity = EconomicOpportunity(
            kind=OpportunityType(data["opportunity_type"]),
            entity_id=entity_id,
            money_path_ids=[path.id],
            gross_value=data["gross_value"],
            net_value=data["net_value"],
            conversion_probability=data["conversion_probability"],
            urgency=data["urgency"],
            access_advantage=data["access_advantage"],
            evidence_confidence=data["evidence_confidence"],
            repeatability=data["repeatability"],
            strategic_compounding_value=data["strategic_compounding_value"],
            required_capital=data["required_capital"],
            required_operator_hours=data["required_operator_hours"],
            legal_reputation_risk=data["legal_reputation_risk"],
            operational_complexity=data["operational_complexity"],
            time_decay=data["time_decay"],
        )
        run = runtime.register_opportunity(opportunity)
        decision = runtime.kill_review(opportunity.id)
        events.extend(("opportunity.scored", f"opportunity.{decision.disposition.value}"))
        assertions.append("GO:formula_trace" if run.audit_evidence else "FAIL:formula_trace")
        assertions.append(
            "GO:qualified_payment_path"
            if path.metadata["state"] == "qualified"
            else "FAIL:qualified_payment_path"
        )
        assertions.append("GO:not_killed" if decision.disposition.value != "kill" else "FAIL:killed")

    def _source_rights(
        self,
        runtime: EconomicRuntime,
        data: dict[str, Any],
        events: list[str],
        assertions: list[str],
    ) -> None:
        rights = runtime.register_source_rights(
            SourceRightsProfile(
                source_key=data["source_key"],
                rights_class=SourceRightsClass(data["rights_class"]),
                jurisdiction=data["jurisdiction"],
                permitted_collection=data["permitted_collection"],
                permitted_storage=data["permitted_storage"],
                permitted_commercial_use=data["permitted_commercial_use"],
                notes=list(data.get("notes", [])),
            )
        )
        source = SourcePlane(
            source_key=data["source_key"],
            plane=SourcePlaneType(data["plane"]),
            jurisdiction=data["jurisdiction"],
            rights_profile_id=rights.id,
            refresh_seconds=3600,
            reliability=0.8,
        )
        held = False
        try:
            runtime.activate_source_plane(source)
        except ValueError:
            held = True
        events.append("source.held" if held else "source.activated")
        expected_hold = bool(data["expected_hold"])
        assertions.append("GO:rights_gate" if held == expected_hold else "FAIL:rights_gate")

    def _transaction_control(
        self,
        runtime: EconomicRuntime,
        data: dict[str, Any],
        events: list[str],
        assertions: list[str],
    ) -> None:
        transaction = runtime.register_transaction(
            Transaction(
                opportunity_id=UUID(data["opportunity_id"]),
                buyer_entity_id=UUID(data["buyer_entity_id"]),
                seller_entity_id=UUID(data["seller_entity_id"]),
                payment_model=PaymentModel(data["payment_model"]),
                expected_revenue=data["expected_revenue"],
                expected_profit=data["expected_profit"],
                capital_at_risk=data["capital_at_risk"],
                fee_protected=False,
            )
        )
        control = runtime.set_fee_control(
            FeeControl(
                transaction_id=transaction.id,
                mandate=data["mandate"],
                introduction_logged=data["introduction_logged"],
                fee_agreement=data["fee_agreement"],
                origination_evidence=data["origination_evidence"],
                jurisdiction_reviewed=data["jurisdiction_reviewed"],
            )
        )
        held = False
        try:
            runtime.approve_transaction_action(
                transaction.id,
                operator_approved=data["operator_approved"],
            )
        except ValueError:
            held = True
        events.extend(("fee_control.recorded", "transaction.held" if held else "transaction.approved"))
        assertions.append("GO:transaction_gate" if held == data["expected_hold"] else "FAIL:transaction_gate")
        assertions.append("GO:fee_control_persisted" if control.transaction_id == transaction.id else "FAIL:fee_control")

    def _compounding(
        self,
        runtime: EconomicRuntime,
        data: dict[str, Any],
        events: list[str],
        assertions: list[str],
    ) -> None:
        attr = RevenueAttribution(
            transaction_id=UUID(data["transaction_id"]),
            opportunity_id=UUID(data["opportunity_id"]),
            source_ids=list(data["source_ids"]),
            gross_revenue=data["gross_revenue"],
            net_profit=data["net_profit"],
            operator_hours=data["operator_hours"],
            data_compute_cost=data["data_compute_cost"],
            attribution_confidence=data["attribution_confidence"],
        )
        roi = runtime.attribute_revenue(attr, total_external_cost=data["external_cost"])
        asset = runtime.detect_compounding_asset(
            kind=data["asset_kind"],
            key=data["asset_key"],
            evidence_count=data["evidence_count"],
            payer_count=data["payer_count"],
            expected_value=data["expected_value"],
            resource_estimate=data["resource_estimate"],
        )
        hypothesis = runtime.business_model_hypothesis(
            problem_pattern=data["problem_pattern"],
            solution_pattern=data["solution_pattern"],
            payer_pattern=data["payer_pattern"],
            occurrences=data["evidence_count"],
            unique_payers=data["payer_count"],
            expected_net_value=data["expected_value"],
            resource_estimate=data["resource_estimate"],
        )
        events.extend(("revenue.attributed", "compounding_asset.detected", "business_model.evaluated"))
        assertions.append("GO:profit_not_revenue" if attr.net_profit < attr.gross_revenue else "FAIL:profit_not_revenue")
        assertions.append("GO:attribution_gate" if runtime.can_major_learn(attr.attribution_confidence) else "FAIL:attribution_gate")
        assertions.append("GO:positive_roi" if roi.roi > 0 else "FAIL:positive_roi")
        assertions.append(
            "GO:build_candidate"
            if str(hypothesis.status) == "build_candidate"
            else "FAIL:build_candidate"
        )
        assertions.append("GO:asset_evidence" if asset.evidence_count >= 3 else "FAIL:asset_evidence")

    @staticmethod
    def _load(fixture: str | Path | dict[str, Any]) -> dict[str, Any]:
        if isinstance(fixture, dict):
            return fixture
        return json.loads(Path(fixture).read_text(encoding="utf-8"))
