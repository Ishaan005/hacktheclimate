from __future__ import annotations

import pytest

pytest.importorskip("langgraph")

from backend.app.chat.operator_decision_graph import build_operator_decision_graph
from backend.app.network_scenarios import Asset
from test_network_forecast import _case, _crosswalk
from test_operator_evaluation import _request


OUTAGE = Asset("branch", "1:3:1")


def _invoke(evaluator):
    graph = build_operator_decision_graph(evaluator=evaluator)
    return graph.invoke({
        "request": _request(),
        "case": _case(),
        "reviewed_crosswalk": _crosswalk(),
        "planned_outage": OUTAGE,
    })


def test_operator_graph_routes_blocked_case_without_llm_reasoning():
    def evaluator(*args, **kwargs):
        return {
            "recommendation": None,
            "best_screening_pass_bundle": None,
            "best_modeled_capture_bundle": "BUNDLE:a",
            "blocking_reasons": ["No complete safety PASS"],
        }

    result = _invoke(evaluator)

    assert result["decision_status"] == "blocked"
    assert result["decision_summary"]["best_modeled_capture_bundle"] == "BUNDLE:a"
    assert any(
        item["action_id"] == "FLEX_LOAD"
        for item in result["resolved_action_families"]
    )


def test_operator_graph_routes_safe_bundle_to_outcome_model_gate():
    def evaluator(*args, **kwargs):
        return {
            "recommendation": None,
            "best_screening_pass_bundle": "BUNDLE:safe",
            "best_modeled_capture_bundle": "BUNDLE:safe",
            "blocking_reasons": [
                "No validated locational model converts network effects into expected avoided dispatch-down MWh"
            ],
        }

    result = _invoke(evaluator)

    assert result["decision_status"] == "outcome_model_required"
    assert result["decision_summary"]["best_screening_pass_bundle"] == "BUNDLE:safe"


def test_operator_graph_routes_only_existing_deterministic_recommendation_to_ready():
    def evaluator(*args, **kwargs):
        return {
            "recommendation": {"bundle_id": "BUNDLE:recommended"},
            "best_screening_pass_bundle": "BUNDLE:recommended",
            "best_modeled_capture_bundle": "BUNDLE:recommended",
            "blocking_reasons": [],
        }

    result = _invoke(evaluator)

    assert result["decision_status"] == "recommendation_ready"
    assert result["decision_summary"]["recommendation"] == {
        "bundle_id": "BUNDLE:recommended"
    }


def test_operator_graph_can_run_the_real_deterministic_evaluator():
    graph = build_operator_decision_graph()
    result = graph.invoke({
        "request": _request(),
        "case": _case(),
        "reviewed_crosswalk": _crosswalk(),
        "planned_outage": OUTAGE,
    })

    assert result["evaluation"]["case_id"] == "synthetic-test"
    assert result["decision_status"] in {"blocked", "outcome_model_required"}
    assert result["evaluation"]["recommendation"] is None
