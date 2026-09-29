from __future__ import annotations

from datetime import datetime, timezone

import pytest

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
            "Planned outage near Ballylickey plus another credible circuit loss "
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
