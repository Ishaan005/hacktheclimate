from pathlib import Path

import pytest

from backend.app.network import NetworkCase, load_case, parse_raw, solve_dc_case, write_case


def small_case() -> NetworkCase:
    buses = [dict(bus_id=i, name=f"B{i}", base_kv=110.0, bus_type=3 if i == 1 else 1, in_service=True, vm_pu=1.0, va_deg=0.0) for i in (1, 2, 3)]
    branches = [dict(asset_id=f"{i}:{j}:1", from_bus=i, to_bus=j, circuit_id="1", r_pu=0.0, x_pu=0.1, rate_a_mva=100.0, rate_b_mva=100.0, rate_c_mva=100.0, in_service=True) for i, j in ((1, 2), (1, 3), (3, 2))]
    generators = [dict(bus_id=1, generator_id="1", pg_mw=100.0, pmax_mw=120.0, pmin_mw=0.0, in_service=True)]
    loads = [dict(bus_id=2, load_id="1", p_mw=100.0, in_service=True)]
    return NetworkCase(buses, branches, [], generators, loads, {"base_mva": 100.0})


def test_dc_triangle_outage_and_islanding():
    case = small_case()
    base = solve_dc_case(case)
    assert base["status"] == "ok"
    flows = {f["asset_id"]: f["flow_mw"] for f in base["flows"]}
    assert flows["1:2:1"] == pytest.approx(200 / 3)
    assert flows["1:3:1"] == pytest.approx(100 / 3)
    outage = solve_dc_case(case, disabled_branches={"1:2:1"})
    assert outage["status"] == "ok"
    assert {f["asset_id"] for f in outage["flows"]} == {"1:3:1", "3:2:1"}
    assert all(f["flow_mw"] == pytest.approx(100) for f in outage["flows"])
    islanded = solve_dc_case(case, disabled_branches={"1:2:1", "3:2:1"})
    assert islanded["status"] == "islanded"
    assert len(islanded["islands"]) == 2
    assert any(not island["has_generator"] and island["imbalance_mw"] == -100 for island in islanded["islands"])


def test_injection_override_and_unknown_outage():
    case = small_case()
    altered = solve_dc_case(case, injection_overrides_mw={2: -50.0})
    assert altered["balance_mw"] == pytest.approx(50.0)
    assert altered["islands"][0]["slack_bus"] == 1
    assert max(abs(f["flow_mw"]) for f in altered["flows"]) == pytest.approx(100 / 3)
    with pytest.raises(ValueError, match="Unknown disabled"):
        solve_dc_case(case, disabled_branches={"no-such-branch"})


def test_csv_round_trip(tmp_path: Path):
    case = small_case()
    write_case(case, tmp_path)
    loaded = load_case(tmp_path)
    assert loaded == case
    assert solve_dc_case(loaded)["flows"] == solve_dc_case(case)["flows"]


def test_three_winding_star_and_parent_disable():
    case = small_case()
    case.branches.clear()
    case.transformers.append(dict(transformer_id="1:2:3:1", from_bus=1, to_bus=2, third_bus=3, circuit_id="1", r_pu=0.0, x_pu=0.2, x23_pu=0.2, x31_pu=0.2, tap_ratio=1.0, phase_shift_deg=0.0, rate_a_mva=100.0, rate_b_mva=100.0, rate_c_mva=100.0, in_service=True))
    solved = solve_dc_case(case)
    assert solved["status"] == "ok"
    assert len(solved["flows"]) == 3
    assert {f["asset_id"] for f in solved["flows"]} == {"1:2:3:1/w1", "1:2:3:1/w2", "1:2:3:1/w3"}
    assert abs(solved["flows"][0]["flow_mw"]) == pytest.approx(100)
    disabled = solve_dc_case(case, disabled_transformers={"1:2:3:1"})
    assert disabled["status"] == "islanded"
    assert disabled["flows"] == []


def test_raw_v33_source_fields_and_transformer_unit_conversion():
    raw = "\n".join([
        "0, 100.0, 33, 1, 1, 50 / PSS/E 33",
        "/ CASE: 2024; SUMMER 01/07/2024",
        "/ fixture",
        "1,'ONE',110,3,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9",
        "2,'TWO',110,1,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9",
        "3,'THREE',110,1,1,1,1,1.0,0.0,1.1,0.9,1.1,0.9",
        "0 / END OF BUS DATA, BEGIN LOAD DATA",
        "2,'LD',1,1,1,50,0,0,0,0,0,1,1,0",
        "0 / END OF LOAD DATA, BEGIN FIXED SHUNT DATA",
        "0 / END OF FIXED SHUNT DATA, BEGIN GENERATOR DATA",
        "1,'G',50,0,0,0,1,0,100,0,0,0,0,1,1,0,100,0",
        "0 / END OF GENERATOR DATA, BEGIN BRANCH DATA",
        "1,2,'A',0.01,0.1,0,100,100,110,0,0,0,0,1,1,1,1,1",
        "0 / END OF BRANCH DATA, BEGIN TRANSFORMER DATA",
        "2,3,0,'T',1,2,1,0,0,2,'TX',1",
        "0.01,0.1,50",
        "1.05,0,0,100,100,100",
        "1.0,0",
        "0 / END OF TRANSFORMER DATA, BEGIN AREA DATA",
        "0 / END OF AREA DATA, BEGIN TWO-TERMINAL DC DATA",
        "0 / END OF TWO-TERMINAL DC DATA, BEGIN VSC DC LINE DATA",
    ]).encode()
    case = parse_raw(raw)
    assert [bus["name"] for bus in case.buses] == ["ONE", "TWO", "THREE"]
    assert case.branches[0]["asset_id"] == "1:2:A"
    assert case.transformers[0]["transformer_id"] == "2:3:T"
    assert case.transformers[0]["x_pu"] == pytest.approx(0.2)
    assert case.transformers[0]["tap_ratio"] == pytest.approx(1.05)
    assert solve_dc_case(case)["status"] == "ok"
