from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import intake


def client(monkeypatch, llm=None):
    if llm is None:
        def llm(_text):
            raise RuntimeError("not configured")
    monkeypatch.setattr(intake, "extract_with_llm", llm)
    app = FastAPI()
    app.include_router(intake.router)
    return TestClient(app)


def test_rules_extract_only_stated_facts(monkeypatch):
    body = client(monkeypatch).post("/v1/intake", json={
        "description": "Thermal overload on the line 14:00-17:00. Charge Battery B2 at 40 MW.",
        "created_at": "2026-09-29T12:00:00Z",
    }).json()
    case = body["case"]
    assert body["extraction"] == "rules"
    assert case["scenarios"] == ["local_network_constraint"]
    assert case["facts"]["event_window"]["value"] == "14:00–17:00"
    assert case["facts"]["event_window"]["source"] == "operator"
    assert "expected_dispatch_down_mwh" not in case["facts"]  # forecast facts are never taken from text
    assert case["proposedAction"]["family"] == "storage_charging"
    assert case["proposedAction"]["assetName"] == "Battery B2"
    assert case["proposedAction"]["facts"]["max_charging_mw"]["value"] == 40.0


def test_unknown_cause_and_comparison(monkeypatch):
    case = client(monkeypatch).post("/v1/intake", json={
        "description": "Wind is being held back.", "comparison_text": "Use demand response to increase load",
        "created_at": "2026-09-29T12:00:00Z",
    }).json()["case"]
    assert case["scenarios"] == ["cause_unknown"]
    assert case["proposedAction"] is None
    assert case["comparison"]["kind"] == "action"
    assert case["comparison"]["action"]["facts"]["direction"]["value"] == "increase"


def test_llm_output_is_filtered(monkeypatch):
    def fake_llm(_text):
        return {"scenarios": ["system_wide_curtailment", "made_up"],
                "facts": {"affected_area": "Donegal", "expected_dispatch_down_mwh": 99, "event_window": None},
                "action": {"family": "generator_redispatch", "asset_name": "Unit 3", "facts": {"scheduled_output_mw": 120, "bogus": 1}}}
    body = client(monkeypatch, fake_llm).post("/v1/intake", json={"description": "x", "created_at": "2026-09-29T12:00:00Z"}).json()
    case = body["case"]
    assert body["extraction"] == "llm"
    assert case["scenarios"] == ["system_wide_curtailment"]
    assert set(case["facts"]) == {"affected_area"}
    assert set(case["proposedAction"]["facts"]) == {"scheduled_output_mw"}
