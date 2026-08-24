from fastapi.testclient import TestClient

from apps.operator.main import app


def test_operator_organism_cockpit_json_and_html_render():
    client = TestClient(app)

    snapshot = client.get("/operator/organism")
    assert snapshot.status_code == 200
    payload = snapshot.json()
    assert payload["autonomy_boundary"] == "tiers_0_to_4_only_tier_5_hold_tier_6_prohibited"
    assert payload["self_state"]["focus"] == "Persistence-backed organism cockpit is active"
    assert payload["curiosity_queue"]

    html = client.get("/operator/organism/ui")
    assert html.status_code == 200
    assert "Brain Organism Operator" in html.text
    assert "Functional consciousness proxy cockpit" in html.text
