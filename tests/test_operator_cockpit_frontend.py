from fastapi.testclient import TestClient

from apps.operator.main import app


def test_economic_cockpit_is_mobile_ready_and_never_cached() -> None:
    client = TestClient(app)
    response = client.get("/operator/ui")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert 'name="viewport"' in response.text
    assert 'http-equiv="refresh"' in response.text


def test_organism_cockpit_is_mobile_ready_and_never_cached() -> None:
    client = TestClient(app)
    response = client.get("/operator/organism/ui")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert 'name="viewport"' in response.text
    assert 'http-equiv="refresh"' in response.text


def test_cockpit_pages_share_one_style_block() -> None:
    client = TestClient(app)
    economic_html = client.get("/operator/ui").text
    organism_html = client.get("/operator/organism/ui").text

    def style_block(text: str) -> str:
        return text.split("<style>", 1)[1].split("</style>", 1)[0]

    assert style_block(economic_html) == style_block(organism_html)


def test_breadcrumb_marks_active_cockpit_and_links_to_the_other() -> None:
    client = TestClient(app)
    economic_html = client.get("/operator/ui").text
    organism_html = client.get("/operator/organism/ui").text

    assert '<span class="here">Economic</span>' in economic_html
    assert '<a href="/operator/organism/ui">Organism</a>' in economic_html

    assert '<span class="here">Organism</span>' in organism_html
    assert '<a href="/operator/ui">Economic</a>' in organism_html
