from __future__ import annotations

import pytest

from backend.app.decision import load_action_catalogue, resolve_action_ids


def test_action_catalogue_is_versioned_and_covers_locked_scenarios():
    catalogue = load_action_catalogue()
    assert catalogue.status == "working_draft"
    assert catalogue.source.endswith("/issues/51")
    assert {action.action_id for action in catalogue.actions} == {
        "FLEX_LOAD", "STORAGE_CHARGE", "GENERATOR_REDISPATCH", "RENEWABLE_LIMIT",
        "INTERCONNECTOR_TRANSFER", "NETWORK_SWITCHING", "OUTAGE_RETURN",
        "UNIT_COMMITMENT", "RESERVE_RAMP_ACTION",
    }
    assert {scenario for action in catalogue.actions for scenario in action.applicable_scenarios} == {
        "T1", "T2", "T3", "T4", "H1", "H2", "H3", "H4", "SNSP",
    }


def test_t1_resolver_returns_only_contract_actions_and_supported_executor():
    actions = resolve_action_ids(["T1"])
    by_id = {action.action_id: action for action in actions}
    assert "FLEX_LOAD" in by_id
    assert "RESERVE_RAMP_ACTION" not in by_id
    assert by_id["FLEX_LOAD"].execution_status == "planning_supported"
    assert by_id["NETWORK_SWITCHING"].execution_status == "not_supported"
    assert "network_loading" in by_id["FLEX_LOAD"].required_safety_rules


def test_multi_scenario_resolution_labels_partial_actions():
    actions = resolve_action_ids(["T1", "SNSP"])
    by_id = {action.action_id: action for action in actions}
    assert by_id["FLEX_LOAD"].eligibility == "eligible"
    assert by_id["FLEX_LOAD"].uncovered_scenarios == []
    assert by_id["NETWORK_SWITCHING"].eligibility == "partial"
    assert by_id["NETWORK_SWITCHING"].uncovered_scenarios == ["SNSP"]


def test_planning_readiness_requires_parameters_and_evidence():
    parameters = {
        "load_bus_id", "renewable_bus_id", "allocation_region", "generation_type",
        "power_mw", "available_from", "available_until", "review_status",
        "evidence_reference",
    }
    action = next(item for item in resolve_action_ids(
        ["T1"],
        available_parameters=parameters,
        available_evidence_fields={"recoverable_renewable_mw"},
    ) if item.action_id == "FLEX_LOAD")
    assert action.planning_ready
    assert action.missing_parameters == []
    assert action.missing_evidence_fields == []


def test_unknown_scenario_cannot_enter_action_resolution():
    with pytest.raises(ValueError, match="unknown locked scenario"):
        resolve_action_ids(["made-up-scenario"])
