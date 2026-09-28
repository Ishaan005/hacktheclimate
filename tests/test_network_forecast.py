from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from backend.app.network import NetworkCase, solve_dc_case
from backend.app.network_forecast import build_network_forecast, future_injection_adapter, load_forecast_inputs, normalized_load_shares, reviewed_generation_groups
from backend.app.network_scenarios import Asset


def _case() -> NetworkCase:
    buses = [
        {"bus_id": bus, "bus_type": 3 if bus == 1 else 1, "in_service": True}
        for bus in (1, 2, 3, 4)
    ]
    branches = [
        {"asset_id": f"{i}:{j}:1", "from_bus": i, "to_bus": j, "x_pu": 0.1, "rate_a_mva": 100.0, "in_service": True}
        for i, j in ((1, 2), (2, 4), (1, 3), (3, 4), (2, 3))
    ]
    return NetworkCase(
        buses=buses,
        branches=branches,
        transformers=[],
        generators=[
            {"bus_id": 1, "pg_mw": 100.0, "pmax_mw": 200.0, "pmin_mw": 0.0, "in_service": True},
            {"bus_id": 2, "pg_mw": 0.0, "pmax_mw": 80.0, "pmin_mw": 0.0, "in_service": True},
        ],
        loads=[{"bus_id": 4, "p_mw": 100.0, "in_service": True}],
        metadata={"base_mva": 100.0},
    )


def _crosswalk() -> list[dict]:
    return [{
        "allocation_region": "South-West",
        "generation_type": "wind",
        "bus_id": 2,
        "mec_mw": 80.0,
        "review_status": "accepted_verified",
        "connection_status": "connected",
    }]


def _rows() -> list[dict]:
    start = datetime(2026, 9, 29, 0, 0, tzinfo=timezone.utc)
    return [
        {
            "issue_time": "2026-09-28T18:00:00Z",
            "forecast_source": "synthetic-test-input",
            "valid_time": (start + timedelta(minutes=30 * index)).isoformat().replace("+00:00", "Z"),
            "constraint_probability": 0.65,
            "expected_constraint_mwh": 20.0,
            "forecast_confidence": 0.75,
            "demand_mw": 100.0,
            "regional_generation_mw": {"South-West": {"wind": 40.0}},
            "dc_transfers_mw": {},
            "drivers": ["high South-West wind"],
        }
        for index in range(48)
    ]


def test_future_adapter_balances_without_slack_absorption():
    case = _case()
    groups, confidence = reviewed_generation_groups(case, _crosswalk())
    injections, dc, diagnostics = future_injection_adapter(
        case,
        _rows()[0],
        load_shares=normalized_load_shares(case),
        generation_groups=groups,
    )
    assert confidence == "high"
    assert dc == {}
    assert sum(injections.values()) == pytest.approx(0.0, abs=1e-8)
    assert injections[2] == pytest.approx(40.0)
    assert injections[1] == pytest.approx(60.0)
    assert injections[4] == pytest.approx(-100.0)
    assert diagnostics["balancing_generation_mw"] == pytest.approx(60.0)


def test_external_dc_import_reduces_thermal_dispatch_without_false_island():
    case = _case()
    case.buses.append({"bus_id": 5, "bus_type": 3, "in_service": True})
    case.metadata["external_dc_boundary_bus_ids"] = [5]
    case.dc_lines.append({
        "dc_line_id": "IMPORT", "scheduled_mw": 20.0,
        "rectifier_bus": 5, "inverter_bus": 3, "in_service": True,
    })
    groups, _ = reviewed_generation_groups(case, _crosswalk())
    row = _rows()[0]
    injections, overrides, diagnostics = future_injection_adapter(
        case, row, load_shares=normalized_load_shares(case), generation_groups=groups,
    )
    result = solve_dc_case(
        case, injection_overrides_mw=injections,
        dc_transfer_overrides_mw=overrides,
    )
    assert diagnostics["external_dc_import_mw"] == pytest.approx(20.0)
    assert diagnostics["balancing_generation_mw"] == pytest.approx(40.0)
    assert diagnostics["modeled_ac_balance_after_dc_mw"] == pytest.approx(0.0)
    assert result["status"] == "ok"
    assert result["dc_transfers_mw"] == {"IMPORT": 20.0}
    assert next(i for i in result["islands"] if i["slack_bus"] == 5)["external_dc_boundary"]


def test_forecast_file_requires_point_in_time_batch_provenance(tmp_path):
    path = tmp_path / "inputs.json"
    rows = _rows()
    path.write_text(json.dumps(rows))
    as_of = datetime(2026, 9, 28, 23, 45, tzinfo=timezone.utc)
    assert len(load_forecast_inputs(path, as_of=as_of)) == 48

    rows[0]["issue_time"] = "2026-09-29T00:15:00Z"
    path.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="one issue_time"):
        load_forecast_inputs(path, as_of=as_of)

    rows = _rows()
    rows[0].pop("issue_time")
    path.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="missing fields"):
        load_forecast_inputs(path)

    rows = _rows()
    rows[0]["issue_time"] = "2026-09-27T00:00:00Z"
    for row in rows[1:]:
        row["issue_time"] = rows[0]["issue_time"]
    path.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="more than 24 hours old"):
        load_forecast_inputs(path, as_of=as_of)


def test_builds_48_half_hour_network_forecast_contract():
    forecast = build_network_forecast(
        _case(),
        _rows(),
        _crosswalk(),
        planned_outage=Asset("branch", "1:3:1"),
        contingency_candidates=3,
    )
    assert len(forecast) == 48
    first = forecast[0]
    assert set(first) == {
        "valid_time", "constraint_probability", "expected_constraint_mwh",
        "network", "drivers", "confidence",
    }
    assert set(first["network"]) == {
        "scenario", "worst_asset", "max_dc_loading_proxy_pct",
        "minimum_headroom_proxy_mw", "worst_contingency", "n_assets_above_80pct",
        "scenarios", "screened_contingency_count", "screened_islanding_contingencies",
        "security_event", "screening_scope",
        "safety",
    }
    assert first["constraint_probability"] == pytest.approx(0.65)
    assert first["expected_constraint_mwh"] == pytest.approx(20.0)
    assert first["confidence"]["network_asset_mapping"] == "high"
    assert first["confidence"]["network_state"] == "planning-scenario"
    assert first["network"]["scenario"] in {"planned-outage", "screened-n-1"}
    assert set(first["network"]["scenarios"]) == {
        "intact", "planned_outage", "selected_n_minus_one",
    }
    assert first["network"]["screened_contingency_count"] <= 3


def test_forecast_rejects_missing_planned_outage():
    with pytest.raises(ValueError, match="in-service case asset"):
        build_network_forecast(
            _case(), _rows(), _crosswalk(),
            planned_outage=Asset("branch", "unknown"),
        )
