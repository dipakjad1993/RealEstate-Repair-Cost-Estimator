"""Tier 1 API wiring tests — new routes must work without network access."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    import api_server

    monkeypatch.setattr(api_server, "AUTH_DISABLED", True)
    monkeypatch.setattr(api_server, "observe_badges", lambda *a, **k: None)
    return TestClient(api_server.app)


def test_estimate_then_citable_twin(client):
    payload = {
        "state": "CA",
        "zip_code": "90001",
        "findings": [{"description": "Roof leak", "severity": "HIGH", "system": "ROOF"}],
    }
    r = client.post("/v1/estimate_repair", json=payload)
    assert r.status_code == 200, r.text
    eid = r.json()["estimate_id"]
    twin = client.get(f"/e/{eid}")
    assert twin.status_code == 200
    body = twin.json()
    assert body["citable"]["markdown"].startswith("# Repair Cost Estimate")
    assert body["citable"]["canonical_url"].endswith(f"/e/{eid}")
    assert client.get("/e/not-an-estimate").status_code == 404


def test_compliance_and_metrics(client):
    r = client.get("/v1/compliance/eu-ai-act")
    assert r.status_code == 200
    assert "ai_act_classification" in r.json()
    m = client.get("/metrics")
    assert m.status_code == 200
    assert "scope" in m.text.lower() or "estimate" in m.text.lower()


def test_live_comps_key_present_is_unsupported():
    from engines.comps_engine import fetch_live_comps

    assert fetch_live_comps("attom", "", "1 Main St") == ([], "REQUIRES_KEY")
    comps, status = fetch_live_comps("attom", "dummy-key", "1 Main St")
    assert comps == []
    assert status == "PROVIDER_UNSUPPORTED"
