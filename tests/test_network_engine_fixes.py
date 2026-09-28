from __future__ import annotations

import pytest

from backend.app.network import NetworkCase, _edges, parse_raw, solve_dc_case
from backend.app.network_scenarios import Asset, compare_network_scenarios


def test_three_winding_cz2_scales_each_pair_and_uses_winding_attributes():
    raw = "\n".join([
        "0, 100.0, 33, 1, 1, 50 / PSS/E 33",
        "/ CASE: 2024; SUMMER 01/07/2024",
        "/ fixture",
        "1,'ONE',110,3,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9",
        "2,'TWO',110,1,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9",
        "3,'THREE',110,1,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9",
        "4,'FOUR',110,1,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9",
        "0 / END OF BUS DATA, BEGIN LOAD DATA",
        "4,'LD',1,1,1,50,0,0,0,0,0,1,1,0",
        "0 / END OF LOAD DATA, BEGIN FIXED SHUNT DATA",
        "0 / END OF FIXED SHUNT DATA, BEGIN GENERATOR DATA",
        "1,'G',50,0,0,0,1,0,100,0,0,0,0,1,1,0,200,0",
        "0 / END OF GENERATOR DATA, BEGIN BRANCH DATA",
        "1,4,'A',0.01,0.1,0,100,100,110,0,0,0,0,1,1,1,1,1",
        "0 / END OF BRANCH DATA, BEGIN TRANSFORMER DATA",
        "1,2,3,'T3',1,2,1,0,0,2,'TX3',1",
        "0.01,0.10,50,0.02,0.20,25,0.03,0.30,20,1.0,0.0",
        "1.05,110,5,100,90,80",
        "0.98,110,-2,80,70,60",
        "1.02,110,1,60,50,40",
        "0 / END OF TRANSFORMER DATA, BEGIN AREA DATA",
        "0 / END OF AREA DATA, BEGIN TWO-TERMINAL DC DATA",
        "'EWIC',1,0.0,25,0,0,0,0,'I',0,20,1.0",
        "1,6,30,5,0.01,0.1,110,1,1,1.5,0.5,0.01,0,0,0,'1',0",
        "4,6,30,5,0.01,0.1,110,1,1,1.5,0.5,0.01,0,0,0,'1',0",
        "0 / END OF TWO-TERMINAL DC DATA, BEGIN VSC DC LINE DATA",
    ]).encode()

    case = parse_raw(raw)
    transformer = case.transformers[0]
    assert transformer["r_pu"] == pytest.approx(0.02)
    assert transformer["x_pu"] == pytest.approx(0.20)
    assert transformer["r23_pu"] == pytest.approx(0.08)
    assert transformer["x23_pu"] == pytest.approx(0.80)
    assert transformer["r31_pu"] == pytest.approx(0.15)
    assert transformer["x31_pu"] == pytest.approx(1.50)

    edges = {edge["asset_id"]: edge for edge in _edges(case, set(), set())}
    assert edges["1:2:3:T3/w1"]["tap_ratio"] == pytest.approx(1.05)
    assert edges["1:2:3:T3/w1"]["phase_shift_deg"] == pytest.approx(5)
    assert edges["1:2:3:T3/w1"]["rating_mva"] == pytest.approx(100)
    assert edges["1:2:3:T3/w2"]["tap_ratio"] == pytest.approx(0.98)
    assert edges["1:2:3:T3/w2"]["phase_shift_deg"] == pytest.approx(-2)
    assert edges["1:2:3:T3/w2"]["rating_mva"] == pytest.approx(80)
    assert edges["1:2:3:T3/w3"]["tap_ratio"] == pytest.approx(1.02)
    assert edges["1:2:3:T3/w3"]["phase_shift_deg"] == pytest.approx(1)
    assert edges["1:2:3:T3/w3"]["rating_mva"] == pytest.approx(60)

    assert case.dc_lines[0]["dc_line_id"] == "EWIC"
    assert case.dc_lines[0]["scheduled_mw"] == pytest.approx(25)
    assert case.dc_lines[0]["rectifier_bus"] == 1
    assert case.dc_lines[0]["inverter_bus"] == 4


def _dc_case() -> NetworkCase:
    buses = [
        {"bus_id": bus, "bus_type": 3 if bus == 1 else 1, "in_service": True}
        for bus in (1, 2, 3)
    ]
    branches = [
        {"asset_id": f"{i}:{j}:1", "from_bus": i, "to_bus": j, "x_pu": 0.1, "rate_a_mva": 100.0, "in_service": True}
        for i, j in ((1, 2), (1, 3), (3, 2))
    ]
    return NetworkCase(
        buses=buses,
        branches=branches,
        transformers=[],
        generators=[{"bus_id": 1, "pg_mw": 100.0, "pmax_mw": 200.0, "pmin_mw": 0.0, "in_service": True}],
        loads=[{"bus_id": 2, "p_mw": 100.0, "in_service": True}],
        metadata={"base_mva": 100.0},
        dc_lines=[{
            "dc_line_id": "EWIC", "control_mode": 1, "set_value": 20.0, "scheduled_mw": 20.0,
            "rectifier_bus": 1, "inverter_bus": 3, "in_service": True,
        }],
    )


def test_dc_transfer_is_equal_and_opposite_and_overrideable():
    case = _dc_case()
    scheduled = solve_dc_case(case)
    overridden = solve_dc_case(case, dc_transfer_overrides_mw={"EWIC": 40.0})
    assert scheduled["status"] == "ok"
    assert overridden["status"] == "ok"
    assert scheduled["balance_mw"] == pytest.approx(0.0)
    assert overridden["balance_mw"] == pytest.approx(0.0)
    assert scheduled["dc_transfers_mw"] == {"EWIC": 20.0}
    assert overridden["dc_transfers_mw"] == {"EWIC": 40.0}
    scheduled_flows = {flow["asset_id"]: flow["flow_mw"] for flow in scheduled["flows"]}
    overridden_flows = {flow["asset_id"]: flow["flow_mw"] for flow in overridden["flows"]}
    assert overridden_flows != scheduled_flows


def test_dc_transfer_remains_effective_with_all_bus_ac_overrides():
    case = _dc_case()
    ac_injections = {1: 100.0, 2: -100.0, 3: 0.0}
    scheduled = solve_dc_case(case, injection_overrides_mw=ac_injections)
    overridden = solve_dc_case(
        case,
        injection_overrides_mw=ac_injections,
        dc_transfer_overrides_mw={"EWIC": 40.0},
    )
    assert scheduled["status"] == overridden["status"] == "ok"
    flows_a = {flow["asset_id"]: flow["flow_mw"] for flow in scheduled["flows"]}
    flows_b = {flow["asset_id"]: flow["flow_mw"] for flow in overridden["flows"]}
    assert flows_a != flows_b


def _scenario_case() -> NetworkCase:
    buses = [
        {"bus_id": bus, "bus_type": 3 if bus == 1 else 1, "in_service": True}
        for bus in (1, 2, 3, 4)
    ]
    branches = [
        {"asset_id": f"{i}:{j}:1", "from_bus": i, "to_bus": j, "x_pu": 0.1, "rate_a_mva": 100.0, "in_service": True}
        for i, j in ((1, 2), (1, 3), (2, 3), (1, 4), (4, 3))
    ]
    return NetworkCase(
        buses=buses,
        branches=branches,
        transformers=[],
        generators=[{"bus_id": 1, "pg_mw": 100.0, "in_service": True}],
        loads=[{"bus_id": 3, "p_mw": 100.0, "in_service": True}],
        metadata={"base_mva": 100.0},
    )


def test_islanded_scenario_suppresses_operating_flows_and_deltas():
    case = _scenario_case()
    case.branches[:] = [row for row in case.branches if row["asset_id"] != "4:3:1"]
    report = compare_network_scenarios(
        case,
        planned_outage=Asset("branch", "1:2:1"),
        contingency=Asset("branch", "1:3:1"),
        monitored=Asset("branch", "2:3:1"),
        outage_reference="reviewed planning row",
        contingency_reference="selected adjacent branch",
    )
    n1 = report["runs"]["selected_n_minus_one"]
    assert n1["status"] == "islanded"
    assert n1["security_event"] is True
    assert n1["operable_state"] is False
    assert n1["actionable"] is False
    assert n1["flows"] == []
    assert report["flow_deltas_from_intact"]["selected_n_minus_one"] is None
    assert report["flow_deltas_from_planned_outage"] is None


def test_system_wide_stress_ranking_reports_loadings_headroom_and_breaches():
    report = compare_network_scenarios(
        _scenario_case(),
        planned_outage=Asset("branch", "1:2:1"),
        contingency=Asset("branch", "1:3:1"),
        monitored=Asset("branch", "1:4:1"),
        outage_reference="reviewed planning row",
        contingency_reference="selected adjacent branch",
    )
    n1 = report["stress_ranking"]["runs"]["selected_n_minus_one"]
    assert n1["actionable"] is True
    assert n1["top_10_highest_loading_proxies"]
    assert n1["threshold_breaches"]["above_80pct"]["count"] >= 1
    comparison = report["stress_ranking"]["comparisons_from_intact"]["selected_n_minus_one"]
    assert comparison["top_10_largest_headroom_decreases"]
    assert comparison["top_10_largest_absolute_flow_changes"]
    assert report["stress_ranking"]["worst_asset"] is not None
