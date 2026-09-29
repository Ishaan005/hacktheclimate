"""LangGraph orchestration for the deterministic operator decision pipeline.

The graph deliberately delegates all domain calculations to the existing
scenario/action resolver and operator evaluator. LangGraph controls execution
order and terminal state only; it never calculates safety margins or chooses
an action itself.
"""

from __future__ import annotations

from typing import Any, Callable, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.decision import load_action_catalogue, resolve_action_ids
from backend.app.network import NetworkCase
from backend.app.network_scenarios import Asset
from backend.app.operator_evaluation import (
    OperatorEvaluationRequest,
    evaluate_operator_case,
)


DecisionStatus = Literal[
    "recommendation_ready",
    "outcome_model_required",
    "blocked",
]


class OperatorDecisionState(TypedDict, total=False):
    request: OperatorEvaluationRequest
    case: NetworkCase
    reviewed_crosswalk: list[dict[str, Any]]
    planned_outage: Asset
    resolved_action_families: list[dict[str, Any]]
    evaluation: dict[str, Any]
    decision_status: DecisionStatus
    decision_summary: dict[str, Any]


def build_operator_decision_graph(
    evaluator: Callable[..., dict[str, Any]] = evaluate_operator_case,
):
    """Compile the operator workflow around deterministic domain functions."""

    def contract_preflight(state: OperatorDecisionState) -> dict[str, Any]:
        request = state["request"]
        catalogue = load_action_catalogue()
        resolved = resolve_action_ids(
            request.decision_case.scenario_ids,
            catalogue=catalogue,
            available_parameters={
                key
                for candidate in request.action_candidates
                for key in candidate
            },
            available_evidence_fields={
                item.field for item in request.evidence if item.value is not None
            },
        )
        return {
            "resolved_action_families": [
                item.model_dump(mode="json") for item in resolved
            ]
        }

    def deterministic_evaluation(state: OperatorDecisionState) -> dict[str, Any]:
        return {
            "evaluation": evaluator(
                state["request"],
                state["case"],
                state["reviewed_crosswalk"],
                planned_outage=state["planned_outage"],
            )
        }

    def route_result(state: OperatorDecisionState) -> str:
        result = state["evaluation"]
        if result.get("recommendation") is not None:
            return "recommendation_ready"
        if result.get("best_screening_pass_bundle") is not None:
            return "outcome_model_required"
        return "blocked"

    def recommendation_ready(state: OperatorDecisionState) -> dict[str, Any]:
        result = state["evaluation"]
        return {
            "decision_status": "recommendation_ready",
            "decision_summary": {
                "recommendation": result.get("recommendation"),
                "best_screening_pass_bundle": result.get(
                    "best_screening_pass_bundle"
                ),
                "blocking_reasons": result.get("blocking_reasons", []),
            },
        }

    def outcome_model_required(state: OperatorDecisionState) -> dict[str, Any]:
        result = state["evaluation"]
        return {
            "decision_status": "outcome_model_required",
            "decision_summary": {
                "best_screening_pass_bundle": result.get(
                    "best_screening_pass_bundle"
                ),
                "message": (
                    "At least one bundle has a complete safety PASS, but the "
                    "validated locational avoided-dispatch-down outcome model "
                    "is not yet available."
                ),
                "blocking_reasons": result.get("blocking_reasons", []),
            },
        }

    def blocked(state: OperatorDecisionState) -> dict[str, Any]:
        result = state["evaluation"]
        return {
            "decision_status": "blocked",
            "decision_summary": {
                "best_modeled_capture_bundle": result.get(
                    "best_modeled_capture_bundle"
                ),
                "blocking_reasons": result.get("blocking_reasons", []),
            },
        }

    graph = StateGraph(OperatorDecisionState)
    graph.add_node("contract_preflight", contract_preflight)
    graph.add_node("operator_evaluation", deterministic_evaluation)
    graph.add_node("recommendation_ready", recommendation_ready)
    graph.add_node("outcome_model_required", outcome_model_required)
    graph.add_node("blocked", blocked)

    graph.add_edge(START, "contract_preflight")
    graph.add_edge("contract_preflight", "operator_evaluation")
    graph.add_conditional_edges(
        "operator_evaluation",
        route_result,
        {
            "recommendation_ready": "recommendation_ready",
            "outcome_model_required": "outcome_model_required",
            "blocked": "blocked",
        },
    )
    graph.add_edge("recommendation_ready", END)
    graph.add_edge("outcome_model_required", END)
    graph.add_edge("blocked", END)
    return graph.compile()


def run_operator_decision_graph(
    request: OperatorEvaluationRequest,
    case: NetworkCase,
    reviewed_crosswalk: list[dict[str, Any]],
    *,
    planned_outage: Asset,
) -> dict[str, Any]:
    """Run the compiled graph and return its final state."""
    graph = build_operator_decision_graph()
    return graph.invoke({
        "request": request,
        "case": case,
        "reviewed_crosswalk": reviewed_crosswalk,
        "planned_outage": planned_outage,
    })
