"""Scenario comparisons must change topology only and retain traceable limits."""

import pytest

from backend.app.network import NetworkCase
from backend.app.network_scenarios import Asset, compare_network_scenarios


def _triangle_with_parallel_path() -> NetworkCase:
    buses = [
        {"bus_id": bus, "bus_type": 3 if bus == 1 else 1, "in_service": True}
        for bus in (1, 2, 3, 4)
    ]

    def branch(start: int, end: int) -> dict:
        return {
            "asset_id": f"{start}:{end}:1",
            "from_bus": start,
            "to_bus": end,
            "in_service": True,
            "x_pu": 0.1,
            "rate_a_mva": 100.0,
        }

    return NetworkCase(
        buses=buses,
        branches=[branch(*pair) for pair in ((1, 2), (1, 3), (2, 3), (1, 4), (4, 3))],
        transformers=[],
        generators=[{"bus_id": 1, "pg_mw": 100.0, "in_service": True}],
        loads=[{"bus_id": 3, "p_mw": 100.0, "in_service": True}],
        metadata={"base_mva": 100.0},
    )


def _compare(case: NetworkCase) -> dict:
    return compare_network_scenarios(
        case,
        planned_outage=Asset("branch", "1:2:1"),
        contingency=Asset("branch", "1:3:1"),
        monitored=Asset("branch", "1:4:1"),
        outage_reference="Reviewed scheduled source row 10; planning only",
        contingency_reference="Adjacent in-service branch in case",
    )


def test_repeated_input_and_topology_changes_produce_traceable_flows() -> None:
    case = _triangle_with_parallel_path()
    report = _compare(case)
    assert report == _compare(case)
    assert report["scenario_label"] == "planning scenario"
    assert [run["status"] for run in report["runs"].values()] == ["ok", "ok", "ok"]

    monitored = report["monitor_by_run"]
    assert monitored["intact"]["flow_mw"] == pytest.approx(25.0)
    assert monitored["planned_outage"]["flow_mw"] == pytest.approx(100 / 3)
    assert monitored["selected_n_minus_one"]["flow_mw"] == pytest.approx(100.0)
    assert monitored["selected_n_minus_one"]["rating_mva"] == 100.0
    assert monitored["selected_n_minus_one"]["dc_loading_pct_proxy"] == pytest.approx(100.0)

    online = {
        name: {flow["asset_id"] for flow in run["flows"]}
        for name, run in report["runs"].items()
    }
    assert "1:2:1" in online["intact"]
    assert "1:2:1" not in online["planned_outage"]
    assert "1:3:1" not in online["selected_n_minus_one"]
    monitor_delta = next(
        row for row in report["flow_deltas_from_planned_outage"] if row["asset_id"] == "1:4:1"
    )
    assert monitor_delta["delta_flow_mw"] == pytest.approx(200 / 3)


def test_unknown_or_self_monitoring_assets_are_rejected() -> None:
    case = _triangle_with_parallel_path()
    with pytest.raises(ValueError, match="absent or out of service"):
        compare_network_scenarios(
            case,
            planned_outage=Asset("branch", "1:2:1"),
            contingency=Asset("branch", "9:9:1"),
            monitored=Asset("branch", "1:4:1"),
            outage_reference="Reviewed row",
            contingency_reference="Chosen asset",
        )
    with pytest.raises(ValueError, match="must remain online"):
        compare_network_scenarios(
            case,
            planned_outage=Asset("branch", "1:2:1"),
            contingency=Asset("branch", "1:3:1"),
            monitored=Asset("branch", "1:3:1"),
            outage_reference="Reviewed row",
            contingency_reference="Chosen asset",
        )
