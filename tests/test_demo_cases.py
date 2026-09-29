from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import intake, workspace
from backend.app.demo_cases import (
    evaluate_west_outage_demo,
    matches_west_outage_demo,
)


UTC = timezone.utc
NOW = datetime(2026, 9, 29, 13, 36, tzinfo=UTC)


def _case(text: str, scenarios: list[str]) -> dict:
    return {
        "id": "demo-case",
        "originalText": text,
        "createdAt": "2026-09-29T13:36:00Z",
        "scenarios": scenarios,
        "facts": {
            "event_window": {
                "key": "event_window", "value": "next 2 hours", "unit": None,
                "status": "supplied", "source": "operator",
                "sourceName": "Operator description", "asOf": "2026-09-29T13:36:00Z",
                "history": [],
            },
            "affected_area": {
                "key": "affected_area", "value": "West", "unit": None,
                "status": "supplied", "source": "operator",
                "sourceName": "Operator description", "asOf": "2026-09-29T13:36:00Z",
                "history": [],
            },
        },
        "proposedAction": None,
        "comparison": None,
    }


def test_demo_trigger_is_explicit():
    assert matches_west_outage_demo(_case(
        "Planned outage near Ballylickey is causing a line overload.",
        ["local_network_constraint", "planned_outage_exposure"],
    ))
    assert not matches_west_outage_demo(_case(
        "Planned outage in the west is causing a line overload.",
        ["local_network_constraint", "planned_outage_exposure"],
    ))


def test_t3_golden_path_selects_mixed_bundle_and_clears_thermal_screen():
    result = evaluate_west_outage_demo(
        _case(
            "Planned outage in the west is causing a line overload. "
            "High wind around Ballylickey is constrained for the next 2 hours.",
            ["local_network_constraint", "planned_outage_exposure"],
        ),
        ["T3"],
        now=NOW,
    )
    assert result["source"] == "demo"
    assert result["actionPresentation"] == "modeled_candidate"
    assert result["action"] is not None
    assert result["action"]["executability"] == "conditional"
    assert "10 MW flexible demand + 15 MW redispatch" in result["action"]["assetName"]
    assert result["binding"]["status"] == "breach"
    assert "109.1%" in result["binding"]["metric"]
    assert result["baseline"]["dispatchDownWasteMwh"] == pytest.approx(40.0)
    assert result["postAction"]["dispatchDownWasteMwh"] == pytest.approx(20.0)
    assert result["postAction"]["securityResult"] == "within_modelled_limit"
    line = next(item for item in result["guardrails"] if item["name"] == "transmission_line")
    assert line["baseline"] == "breach"
    assert line["postAction"] == "within_modelled_limit"
    assert "81.8%" in line["note"]


def test_t4_variant_refuses_when_further_loss_islands_demo_area():
    result = evaluate_west_outage_demo(
        _case(
            "Planned outage in the west near Ballylickey plus another credible circuit loss "
            "creates an N-1 overload for the next 2 hours.",
            ["local_network_constraint", "planned_outage_exposure"],
        ),
        ["T4"],
        now=NOW,
    )
    assert result["source"] == "demo"
    assert result["action"] is None
    assert result["postAction"] is None
    assert "further-contingency" in result["noActionReason"]
    assert "islands" in result["noActionReason"]


def test_hero_prompt_runs_intake_to_workspace_end_to_end():
    app = FastAPI()
    app.include_router(intake.router)
    app.include_router(workspace.router)
    client = TestClient(app)

    intake_response = client.post("/v1/intake", json={
        "description": (
            "Planned outage in the west is causing a line overload. "
            "High wind around Ballylickey is constrained for the next 2 hours. "
            "What can we do to reduce dispatch-down?"
        ),
        "created_at": "2026-09-29T13:36:00Z",
    })
    assert intake_response.status_code == 200
    body = intake_response.json()
    assert body["extraction"] == "rules"
    reviewed_case = body["case"]
    assert reviewed_case["facts"]["affected_area"]["value"] == "West"
    assert reviewed_case["facts"]["event_window"]["value"] == "next 2 hours"

    evaluation_response = client.post(
        "/v1/workspace/evaluate",
        json={"case": reviewed_case},
    )
    assert evaluation_response.status_code == 200
    scenario = evaluation_response.json()["scenario"]
    assert scenario["source"] == "demo"
    assert scenario["actionPresentation"] == "modeled_candidate"
    assert scenario["action"] is not None
    assert scenario["baseline"]["dispatchDownWasteMwh"] == pytest.approx(40.0)
    assert scenario["postAction"]["dispatchDownWasteMwh"] == pytest.approx(20.0)


def test_azure_case_assistant_receives_computed_demo_result_not_raw_operator_text(monkeypatch):
    from backend.app.chat import config, graph

    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(configured=True, deployment="gpt-4.1"))
    messages_seen = []

    class FakeModel:
        def invoke(self, messages):
            messages_seen.extend(messages)
            return SimpleNamespace(content="The modeled candidate clears the synthetic line screen; other checks remain unknown.")

    monkeypatch.setattr(graph, "build_azure_llm", lambda _settings, **_kwargs: FakeModel())
    app = FastAPI()
    app.include_router(workspace.router)
    client = TestClient(app)
    case = _case(
        "Private operator wording: Planned outage near Ballylickey causes a line overload.",
        ["local_network_constraint", "planned_outage_exposure"],
    )
    response = client.post("/v1/workspace/ask", json={
        "case": case,
        "question": "What does this show?",
        "history": [{"question": "Earlier question?", "reply": "Earlier answer."}],
    })

    assert response.status_code == 200
    assert response.json()["model"] == "gpt-4.1"
    assert "modeled candidate" in response.json()["reply"]
    assert "109.1%" in messages_seen[0].content
    assert "Private operator wording" not in messages_seen[0].content
    assert [message.content for message in messages_seen[1:]] == [
        "Earlier question?", "Earlier answer.", "What does this show?",
    ]


def test_case_assistant_reports_missing_azure_configuration(monkeypatch):
    from backend.app.chat import config

    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(configured=False))
    app = FastAPI()
    app.include_router(workspace.router)
    response = TestClient(app).post("/v1/workspace/ask", json={
        "case": _case(
            "Planned outage near Ballylickey causes a line overload.",
            ["local_network_constraint", "planned_outage_exposure"],
        ),
        "question": "Explain this result.",
    })
    assert response.status_code == 503
    assert "Azure OpenAI is not configured" in response.json()["detail"]


def test_case_assistant_reports_azure_overload_without_hiding_the_computed_case(monkeypatch):
    from backend.app.chat import config, graph

    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(configured=True, deployment="gpt-4.1"))
    overloaded = type("OpenAIAPIError", (Exception,), {})

    class BusyModel:
        def invoke(self, _messages):
            raise overloaded("temporary service failure")

    monkeypatch.setattr(graph, "build_azure_llm", lambda _settings, **_kwargs: BusyModel())
    app = FastAPI()
    app.include_router(workspace.router)
    case = _case(
        "Planned outage near Ballylickey causes a line overload.",
        ["local_network_constraint", "planned_outage_exposure"],
    )
    client = TestClient(app)
    answer = client.post("/v1/workspace/ask", json={"case": case, "question": "Explain this result."})
    evaluation = client.post("/v1/workspace/evaluate", json={"case": case})
    assert answer.status_code == 503
    assert "overloaded" in answer.json()["detail"]
    assert evaluation.status_code == 200
    assert evaluation.json()["scenario"]["source"] == "demo"
