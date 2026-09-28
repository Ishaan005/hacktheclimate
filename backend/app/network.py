"""A deliberately limited PSS/E v33 RAW importer and lossless DC planning solver.

Only the TYTFS 2024 V33 layout is supported. This is a scenario model, not a
representation of the live transmission network or an AC security study.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

RAW_MEMBER = "TYTFS2024_studyfiles/TYTFS2024_SV2024_V33.raw"
SOURCE_URL = "https://cms.eirgrid.ie/sites/default/files/publications/TYTFS2024_studyfiles.zip"

BUS_COLUMNS = ("bus_id", "name", "base_kv", "bus_type", "in_service", "vm_pu", "va_deg")
BRANCH_COLUMNS = ("asset_id", "from_bus", "to_bus", "circuit_id", "r_pu", "x_pu", "rate_a_mva", "rate_b_mva", "rate_c_mva", "in_service")
TRANSFORMER_COLUMNS = (
    "transformer_id", "from_bus", "to_bus", "third_bus", "circuit_id",
    "r_pu", "x_pu", "r23_pu", "x23_pu", "r31_pu", "x31_pu",
    "tap_ratio", "phase_shift_deg", "rate_a_mva", "rate_b_mva", "rate_c_mva",
    "w1_tap_ratio", "w1_phase_shift_deg", "w1_rate_a_mva", "w1_rate_b_mva", "w1_rate_c_mva",
    "w2_tap_ratio", "w2_phase_shift_deg", "w2_rate_a_mva", "w2_rate_b_mva", "w2_rate_c_mva",
    "w3_tap_ratio", "w3_phase_shift_deg", "w3_rate_a_mva", "w3_rate_b_mva", "w3_rate_c_mva",
    "in_service",
)
GENERATOR_COLUMNS = ("bus_id", "generator_id", "pg_mw", "pmax_mw", "pmin_mw", "in_service")
LOAD_COLUMNS = ("bus_id", "load_id", "p_mw", "in_service")
DC_LINE_COLUMNS = (
    "dc_line_id", "control_mode", "set_value", "scheduled_mw",
    "rectifier_bus", "inverter_bus", "in_service",
)


@dataclass(frozen=True)
class NetworkCase:
    buses: list[dict]
    branches: list[dict]
    transformers: list[dict]
    generators: list[dict]
    loads: list[dict]
    metadata: dict
    dc_lines: list[dict] = field(default_factory=list)


def _fields(line: str) -> list[str]:
    return [field.strip() for field in next(csv.reader([line], skipinitialspace=True, quotechar="'"))]


def _sections(raw: str) -> dict[str, list[str]]:
    lines = raw.splitlines()
    if len(lines) < 4:
        raise ValueError("RAW file is empty or truncated")
    header = _fields(lines[0].split("/")[0])
    if len(header) < 3 or int(header[2]) != 33 or float(header[1]) != 100:
        raise ValueError("Only the 100 MVA PSS/E version 33 case is supported")
    labels = ("buses", "loads", "fixed_shunts", "generators", "branches", "transformers", "areas", "dc_lines")
    sections: dict[str, list[str]] = {}
    current = labels[0]
    section_index = 0
    for line in lines[3:]:
        stripped = line.strip()
        if stripped.startswith("0 / END OF"):
            sections[current] = sections.get(current, [])
            section_index += 1
            if section_index >= len(labels):
                break
            current = labels[section_index]
        elif stripped and stripped != "Q":
            sections.setdefault(current, []).append(line)
    for name in labels[:6]:
        if name not in sections:
            raise ValueError(f"Missing RAW section: {name}")
    return sections


def _number(value: str) -> float:
    return float(value)


def _asset_id(i: int, j: int, k: int | None, circuit_id: str) -> str:
    return f"{i}:{j}:{k}:{circuit_id}" if k else f"{i}:{j}:{circuit_id}"


def _three_winding_values(line: list[str], label: str) -> dict:
    if len(line) < 6:
        raise ValueError(f"Truncated three-winding {label} record")
    return {
        "tap_ratio": _number(line[0]),
        "phase_shift_deg": _number(line[2]),
        "rate_a_mva": _number(line[3]),
        "rate_b_mva": _number(line[4]),
        "rate_c_mva": _number(line[5]),
    }


def parse_raw(raw: bytes) -> NetworkCase:
    """Parse the 2024 summer V33 case without changing its source statuses."""
    text = raw.decode("utf-8-sig")
    if "SUMMER 01/07/2024" not in text.splitlines()[1]:
        raise ValueError("Expected the TYTFS summer 1 July 2024 case")
    parts = _sections(text)

    buses = []
    for line in parts["buses"]:
        f = _fields(line)
        buses.append(dict(
            bus_id=int(f[0]), name=f[1], base_kv=_number(f[2]), bus_type=int(f[3]),
            in_service=int(f[3]) != 4, vm_pu=_number(f[7]), va_deg=_number(f[8]),
        ))

    loads = []
    for line in parts["loads"]:
        f = _fields(line)
        loads.append(dict(
            bus_id=int(f[0]), load_id=f[1], p_mw=_number(f[5]), in_service=int(f[2]) == 1,
        ))

    generators = []
    for line in parts["generators"]:
        f = _fields(line)
        generators.append(dict(
            bus_id=int(f[0]), generator_id=f[1], pg_mw=_number(f[2]),
            pmax_mw=_number(f[16]), pmin_mw=_number(f[17]), in_service=int(f[14]) == 1,
        ))

    branches = []
    for line in parts["branches"]:
        f = _fields(line)
        i, j = int(f[0]), int(f[1])
        branches.append(dict(
            asset_id=_asset_id(i, j, None, f[2]), from_bus=i, to_bus=j, circuit_id=f[2],
            r_pu=_number(f[3]), x_pu=_number(f[4]), rate_a_mva=_number(f[6]),
            rate_b_mva=_number(f[7]), rate_c_mva=_number(f[8]), in_service=int(f[13]) == 1,
        ))

    transformers = []
    tlines = parts["transformers"]
    offset = 0
    while offset < len(tlines):
        a = _fields(tlines[offset])
        i, j, k = int(a[0]), int(a[1]), int(a[2])
        length = 5 if k else 4
        if offset + length > len(tlines):
            raise ValueError("Truncated transformer record")
        z = _fields(tlines[offset + 1])
        winding1 = _fields(tlines[offset + 2])
        winding2 = _fields(tlines[offset + 3])
        winding3 = _fields(tlines[offset + 4]) if k else None
        cw, cz = int(a[4]), int(a[5])
        if cw != 1 or cz not in (1, 2):
            raise ValueError("Unsupported transformer CW/CZ unit code")

        if k:
            if len(z) < 9 or winding3 is None:
                raise ValueError("Truncated three-winding impedance record")
            scales = (
                100.0 / _number(z[2]) if cz == 2 else 1.0,
                100.0 / _number(z[5]) if cz == 2 else 1.0,
                100.0 / _number(z[8]) if cz == 2 else 1.0,
            )
            w1 = _three_winding_values(winding1, "winding 1")
            w2 = _three_winding_values(winding2, "winding 2")
            w3 = _three_winding_values(winding3, "winding 3")
            transformers.append(dict(
                transformer_id=_asset_id(i, j, k, a[3]),
                from_bus=i, to_bus=j, third_bus=k, circuit_id=a[3],
                r_pu=_number(z[0]) * scales[0], x_pu=_number(z[1]) * scales[0],
                r23_pu=_number(z[3]) * scales[1], x23_pu=_number(z[4]) * scales[1],
                r31_pu=_number(z[6]) * scales[2], x31_pu=_number(z[7]) * scales[2],
                tap_ratio=w1["tap_ratio"], phase_shift_deg=w1["phase_shift_deg"],
                rate_a_mva=w1["rate_a_mva"], rate_b_mva=w1["rate_b_mva"], rate_c_mva=w1["rate_c_mva"],
                w1_tap_ratio=w1["tap_ratio"], w1_phase_shift_deg=w1["phase_shift_deg"],
                w1_rate_a_mva=w1["rate_a_mva"], w1_rate_b_mva=w1["rate_b_mva"], w1_rate_c_mva=w1["rate_c_mva"],
                w2_tap_ratio=w2["tap_ratio"], w2_phase_shift_deg=w2["phase_shift_deg"],
                w2_rate_a_mva=w2["rate_a_mva"], w2_rate_b_mva=w2["rate_b_mva"], w2_rate_c_mva=w2["rate_c_mva"],
                w3_tap_ratio=w3["tap_ratio"], w3_phase_shift_deg=w3["phase_shift_deg"],
                w3_rate_a_mva=w3["rate_a_mva"], w3_rate_b_mva=w3["rate_b_mva"], w3_rate_c_mva=w3["rate_c_mva"],
                in_service=int(a[11]) == 1,
            ))
        else:
            impedance_scale = 100.0 / _number(z[2]) if cz == 2 else 1.0
            tap = _number(winding1[0]) / _number(winding2[0])
            transformers.append(dict(
                transformer_id=_asset_id(i, j, None, a[3]),
                from_bus=i, to_bus=j, third_bus="", circuit_id=a[3],
                r_pu=_number(z[0]) * impedance_scale, x_pu=_number(z[1]) * impedance_scale,
                r23_pu="", x23_pu="", r31_pu="", x31_pu="",
                tap_ratio=tap, phase_shift_deg=_number(winding1[2]),
                rate_a_mva=_number(winding1[3]), rate_b_mva=_number(winding1[4]), rate_c_mva=_number(winding1[5]),
                w1_tap_ratio=_number(winding1[0]), w1_phase_shift_deg=_number(winding1[2]),
                w1_rate_a_mva=_number(winding1[3]), w1_rate_b_mva=_number(winding1[4]), w1_rate_c_mva=_number(winding1[5]),
                w2_tap_ratio=_number(winding2[0]), w2_phase_shift_deg="",
                w2_rate_a_mva="", w2_rate_b_mva="", w2_rate_c_mva="",
                w3_tap_ratio="", w3_phase_shift_deg="",
                w3_rate_a_mva="", w3_rate_b_mva="", w3_rate_c_mva="",
                in_service=int(a[11]) == 1,
            ))
        offset += length

    dc_lines = []
    dclines = parts.get("dc_lines", [])
    offset = 0
    while offset < len(dclines):
        if offset + 3 > len(dclines):
            raise ValueError("Truncated two-terminal DC line record")
        header = _fields(dclines[offset])
        rectifier = _fields(dclines[offset + 1])
        inverter = _fields(dclines[offset + 2])
        if len(header) < 4 or not rectifier or not inverter:
            raise ValueError("Truncated two-terminal DC line record")
        dc_line_id = header[0].strip().strip('"').strip()
        control_mode = int(float(header[1]))
        if control_mode not in (0, 1, 2):
            raise ValueError(f"Unsupported two-terminal DC control mode: {control_mode}")
        set_value = _number(header[3])
        scheduled_mw = set_value if control_mode == 1 else None
        dc_lines.append(dict(
            dc_line_id=dc_line_id,
            control_mode=control_mode,
            set_value=set_value,
            scheduled_mw=scheduled_mw,
            rectifier_bus=int(rectifier[0]),
            inverter_bus=int(inverter[0]),
            in_service=control_mode != 0,
        ))
        offset += 3

    ids = [b["bus_id"] for b in buses]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate bus ID")
    valid = set(ids)
    for element in branches + transformers:
        endpoints = [element["from_bus"], element["to_bus"]]
        if element.get("third_bus"):
            endpoints.append(element["third_bus"])
        if not set(endpoints) <= valid:
            raise ValueError("Asset references a missing bus")
    for element in loads + generators:
        if element["bus_id"] not in valid:
            raise ValueError("Injection references a missing bus")
    for dc_line in dc_lines:
        if {dc_line["rectifier_bus"], dc_line["inverter_bus"]} - valid:
            raise ValueError("DC line references a missing converter bus")
    dc_ids = [line["dc_line_id"] for line in dc_lines]
    if len(dc_ids) != len(set(dc_ids)):
        raise ValueError("Duplicate two-terminal DC line ID")

    ac_terminals = {
        terminal
        for element in branches + transformers
        for terminal in (element["from_bus"], element["to_bus"], element.get("third_bus"))
        if terminal
    }
    dc_terminals = {
        terminal
        for line in dc_lines
        for terminal in (line["rectifier_bus"], line["inverter_bus"])
    }
    occupied_buses = {
        row["bus_id"] for row in generators + loads if row["in_service"]
    }
    # The selected TYTFS case models Scotland as an isolated AC stub connected
    # to Ireland only through the Moyle DC records. Its external grid is not
    # represented by a RAW generator; retain the boundary assumption explicitly.
    external_dc_boundary_bus_ids = sorted(
        bus["bus_id"]
        for bus in buses
        if bus["name"].strip().upper() == "SCOTLAND"
        and bus["bus_id"] in dc_terminals
        and bus["bus_id"] not in ac_terminals | occupied_buses
    )
    metadata = dict(
        source_url=SOURCE_URL, source_member=RAW_MEMBER, source_sha256=hashlib.sha256(raw).hexdigest(),
        season="summer", study_year=2024, scenario_date="2024-07-01", pss_e_version=33,
        base_mva=100.0, scenario_label="TYTFS 2024 planning scenario",
        source_note="Reference planning power flow; not a live operational state.",
        external_dc_boundary_bus_ids=external_dc_boundary_bus_ids,
    )
    return NetworkCase(buses, branches, transformers, generators, loads, metadata, dc_lines)


def import_zip(path: str | Path) -> NetworkCase:
    with zipfile.ZipFile(path) as archive:
        return parse_raw(archive.read(RAW_MEMBER))


def write_case(case: NetworkCase, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    tables = (
        ("buses.csv", case.buses, BUS_COLUMNS),
        ("branches.csv", case.branches, BRANCH_COLUMNS),
        ("transformers.csv", case.transformers, TRANSFORMER_COLUMNS),
        ("generators.csv", case.generators, GENERATOR_COLUMNS),
        ("loads.csv", case.loads, LOAD_COLUMNS),
        ("dc_lines.csv", case.dc_lines, DC_LINE_COLUMNS),
    )
    for filename, rows, columns in tables:
        with (output / filename).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    (output / "provenance.json").write_text(json.dumps(case.metadata, indent=2) + "\n")


def load_case(output_dir: str | Path) -> NetworkCase:
    directory = Path(output_dir)

    def read(name: str, ints: set[str], floats: set[str]) -> list[dict]:
        with (directory / name).open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            for key in ints:
                if key in row and row[key] != "":
                    row[key] = int(row[key])
            for key in floats:
                if key in row and row[key] != "":
                    row[key] = float(row[key])
            if "in_service" in row:
                row["in_service"] = row["in_service"] == "True"
        return rows

    buses = read("buses.csv", {"bus_id", "bus_type"}, {"base_kv", "vm_pu", "va_deg"})
    branches = read("branches.csv", {"from_bus", "to_bus"}, {"r_pu", "x_pu", "rate_a_mva", "rate_b_mva", "rate_c_mva"})
    transformer_floats = {
        "r_pu", "x_pu", "r23_pu", "x23_pu", "r31_pu", "x31_pu",
        "tap_ratio", "phase_shift_deg", "rate_a_mva", "rate_b_mva", "rate_c_mva",
        "w1_tap_ratio", "w1_phase_shift_deg", "w1_rate_a_mva", "w1_rate_b_mva", "w1_rate_c_mva",
        "w2_tap_ratio", "w2_phase_shift_deg", "w2_rate_a_mva", "w2_rate_b_mva", "w2_rate_c_mva",
        "w3_tap_ratio", "w3_phase_shift_deg", "w3_rate_a_mva", "w3_rate_b_mva", "w3_rate_c_mva",
    }
    transformers = read("transformers.csv", {"from_bus", "to_bus"}, transformer_floats)
    for t in transformers:
        if t["third_bus"] != "":
            t["third_bus"] = int(t["third_bus"])
        for key in TRANSFORMER_COLUMNS:
            if key not in t:
                t[key] = ""
        if t["third_bus"]:
            for winding in (1, 2, 3):
                t[f"w{winding}_tap_ratio"] = t.get(f"w{winding}_tap_ratio") or (t["tap_ratio"] if winding == 1 else 1.0)
                t[f"w{winding}_phase_shift_deg"] = t.get(f"w{winding}_phase_shift_deg") or (t["phase_shift_deg"] if winding == 1 else 0.0)
                t[f"w{winding}_rate_a_mva"] = t.get(f"w{winding}_rate_a_mva") or (t["rate_a_mva"] if winding == 1 else "")
    generators = read("generators.csv", {"bus_id"}, {"pg_mw", "pmax_mw", "pmin_mw"})
    loads = read("loads.csv", {"bus_id"}, {"p_mw"})
    dc_path = directory / "dc_lines.csv"
    dc_lines = (
        read("dc_lines.csv", {"control_mode", "rectifier_bus", "inverter_bus"}, {"set_value", "scheduled_mw"})
        if dc_path.exists() else []
    )
    return NetworkCase(
        buses, branches, transformers, generators, loads,
        json.loads((directory / "provenance.json").read_text()), dc_lines,
    )


def _edges(case: NetworkCase, disabled_branches: set[str], disabled_transformers: set[str]) -> list[dict]:
    active_buses = {b["bus_id"] for b in case.buses if b["in_service"]}
    edges = []
    for b in case.branches:
        if b["in_service"] and b["asset_id"] not in disabled_branches and {b["from_bus"], b["to_bus"]} <= active_buses:
            edges.append(dict(
                asset_type="branch", asset_id=b["asset_id"], from_bus=b["from_bus"], to_bus=b["to_bus"],
                x_pu=b["x_pu"], tap_ratio=1.0, phase_shift_deg=0.0, rating_mva=b["rate_a_mva"],
            ))
    for t in case.transformers:
        if not t["in_service"] or t["transformer_id"] in disabled_transformers:
            continue
        terminals = [t["from_bus"], t["to_bus"]] + ([t["third_bus"]] if t["third_bus"] else [])
        if not set(terminals) <= active_buses:
            continue
        if not t["third_bus"]:
            edges.append(dict(
                asset_type="transformer", asset_id=t["transformer_id"], from_bus=t["from_bus"], to_bus=t["to_bus"],
                x_pu=t["x_pu"], tap_ratio=t["tap_ratio"], phase_shift_deg=t["phase_shift_deg"],
                rating_mva=t["rate_a_mva"],
            ))
        else:
            x12, x23, x31 = t["x_pu"], t["x23_pu"], t["x31_pu"]
            xs = (
                (x12 + x31 - x23) / 2,
                (x12 + x23 - x31) / 2,
                (x23 + x31 - x12) / 2,
            )
            star = -len(edges) - 1
            winding_values = [
                (t.get("w1_tap_ratio") or t["tap_ratio"], t.get("w1_phase_shift_deg") or t["phase_shift_deg"], t.get("w1_rate_a_mva") or t["rate_a_mva"]),
                (t.get("w2_tap_ratio") or 1.0, t.get("w2_phase_shift_deg") or 0.0, t.get("w2_rate_a_mva") or None),
                (t.get("w3_tap_ratio") or 1.0, t.get("w3_phase_shift_deg") or 0.0, t.get("w3_rate_a_mva") or None),
            ]
            for winding, (bus, x, values) in enumerate(zip(terminals, xs, winding_values), 1):
                tap, phase, rating = values
                edges.append(dict(
                    asset_type="transformer", asset_id=f"{t['transformer_id']}/w{winding}",
                    from_bus=bus, to_bus=star, x_pu=x if abs(x) > 1e-8 else 1e-8,
                    tap_ratio=tap, phase_shift_deg=phase, rating_mva=rating,
                ))
    return edges


def solve_dc_case(
    case: NetworkCase,
    *,
    disabled_branches: Iterable[str] = (),
    disabled_transformers: Iterable[str] = (),
    injection_overrides_mw: Mapping[int, float] | None = None,
    dc_transfer_overrides_mw: Mapping[str, float] | None = None,
) -> dict:
    """Solve fixed MW injections by component, assigning residual to one slack bus.

    injection_overrides_mw replaces the final net AC injection at named buses.
    dc_transfer_overrides_mw replaces the scheduled MW transfer for named
    two-terminal DC lines. Positive DC MW withdraws at the rectifier bus and
    injects at the inverter bus. Current-controlled DC lines are only applied
    when an explicit MW override is supplied.
    """
    disabled_branches = set(disabled_branches)
    disabled_transformers = set(disabled_transformers)
    known_branch_ids = {b["asset_id"] for b in case.branches}
    known_transformer_ids = {t["transformer_id"] for t in case.transformers}
    if disabled_branches - known_branch_ids or disabled_transformers - known_transformer_ids:
        raise ValueError("Unknown disabled branch or transformer ID")

    active_buses = {b["bus_id"] for b in case.buses if b["in_service"]}
    overrides = dict(injection_overrides_mw or {})
    if set(overrides) - active_buses:
        raise ValueError("Injection override references an inactive or unknown bus")
    dc_overrides = dict(dc_transfer_overrides_mw or {})
    known_dc_ids = {str(line["dc_line_id"]) for line in case.dc_lines}
    if set(dc_overrides) - known_dc_ids:
        raise ValueError("DC transfer override references an unknown DC line")
    for line in case.dc_lines:
        if str(line["dc_line_id"]) in dc_overrides and (
            not line.get("in_service", True)
            or {int(line["rectifier_bus"]), int(line["inverter_bus"])} - active_buses
        ):
            raise ValueError("DC transfer override references an inactive line or converter bus")

    edges = _edges(case, disabled_branches, disabled_transformers)
    nodes = set(active_buses)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in edges:
        i, j = edge["from_bus"], edge["to_bus"]
        if not edge["x_pu"] or not edge["tap_ratio"]:
            return dict(
                status="unsolved", reason=f"Zero reactance or tap on {edge['asset_id']}",
                flows=[], bus_angles_rad={}, balance_mw=0.0, islands=[],
            )
        nodes.update((i, j))
        adjacency[i].add(j)
        adjacency[j].add(i)

    injections = defaultdict(float)
    for g in case.generators:
        if g["in_service"] and g["bus_id"] in active_buses:
            injections[g["bus_id"]] += g["pg_mw"]
    for load in case.loads:
        if load["in_service"] and load["bus_id"] in active_buses:
            injections[load["bus_id"]] -= load["p_mw"]

    # Injection overrides describe AC net injections. Apply DC transfers after
    # them so an all-bus override cannot silently erase converter transfers.
    for bus_id, value in overrides.items():
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"Injection override for bus {bus_id} must be finite")
        injections[bus_id] = value

    applied_dc_transfers: dict[str, float] = {}
    for line in case.dc_lines:
        dc_id = str(line["dc_line_id"])
        if not line.get("in_service", True):
            continue
        rectifier = int(line["rectifier_bus"])
        inverter = int(line["inverter_bus"])
        if rectifier not in active_buses or inverter not in active_buses:
            continue
        scheduled = dc_overrides.get(dc_id, line.get("scheduled_mw"))
        if scheduled is None:
            continue
        transfer = float(scheduled)
        if not math.isfinite(transfer):
            raise ValueError(f"DC transfer for {dc_id} must be finite")
        injections[rectifier] -= transfer
        injections[inverter] += transfer
        applied_dc_transfers[dc_id] = transfer

    raw_balance = sum(injections.values())
    components = []
    remaining = set(nodes)
    while remaining:
        seed = min(remaining)
        found = {seed}
        queue = deque([seed])
        remaining.remove(seed)
        while queue:
            for neighbor in adjacency[queue.popleft()] & remaining:
                found.add(neighbor)
                remaining.remove(neighbor)
                queue.append(neighbor)
        components.append(found)

    slack_candidates = {b["bus_id"] for b in case.buses if b["bus_type"] == 3 and b["in_service"]}
    generator_buses = {g["bus_id"] for g in case.generators if g["in_service"]}
    angle: dict[int, float] = {}
    island_info = []
    external_boundary_buses = set(case.metadata.get("external_dc_boundary_bus_ids", []))
    for component in components:
        real = component & active_buses
        if not real:
            continue
        candidates = component & slack_candidates or component & generator_buses
        slack = min(candidates) if candidates else min(real)
        imbalance = sum(injections[n] for n in component)
        island_info.append(dict(
            bus_count=len(real), slack_bus=slack, imbalance_mw=imbalance,
            has_generator=bool(component & generator_buses),
            external_dc_boundary=bool(real and real <= external_boundary_buses),
        ))
        comp_edges = [e for e in edges if e["from_bus"] in component]
        ordered = sorted(component)
        index = {bus: position for position, bus in enumerate(ordered)}
        row, col, vals = [], [], []
        rhs = np.array([injections[n] for n in ordered], dtype=float)
        rhs[index[slack]] -= imbalance
        for e in comp_edges:
            i, j = index[e["from_bus"]], index[e["to_bus"]]
            b = case.metadata["base_mva"] / (e["x_pu"] * e["tap_ratio"])
            for r, c, v in ((i, i, b), (j, j, b), (i, j, -b), (j, i, -b)):
                row.append(r)
                col.append(c)
                vals.append(v)
            shift = math.radians(e["phase_shift_deg"])
            rhs[i] += b * shift
            rhs[j] -= b * shift
        if len(ordered) == 1:
            solution = np.array([0.0])
        else:
            matrix = coo_matrix((vals, (row, col)), shape=(len(ordered), len(ordered))).tocsr()
            keep = [n for n in range(len(ordered)) if n != index[slack]]
            try:
                solution = np.zeros(len(ordered))
                solution[keep] = spsolve(matrix[keep][:, keep], rhs[keep])
            except Exception as exc:
                return dict(
                    status="unsolved", reason=str(exc), flows=[], bus_angles_rad={},
                    balance_mw=raw_balance, islands=island_info,
                    dc_transfers_mw=applied_dc_transfers,
                )
            if not np.all(np.isfinite(solution)):
                return dict(
                    status="unsolved", reason="Singular DC matrix", flows=[], bus_angles_rad={},
                    balance_mw=raw_balance, islands=island_info,
                    dc_transfers_mw=applied_dc_transfers,
                )
        angle.update(zip(ordered, map(float, solution)))

    flows = []
    net_from_flows = defaultdict(float)
    for e in edges:
        b = case.metadata["base_mva"] / (e["x_pu"] * e["tap_ratio"])
        flow = b * (
            angle[e["from_bus"]] - angle[e["to_bus"]] - math.radians(e["phase_shift_deg"])
        )
        rating = e["rating_mva"]
        usable = rating is not None and 0 < rating < 9000
        flows.append(dict(
            asset_type=e["asset_type"], asset_id=e["asset_id"],
            from_bus=e["from_bus"], to_bus=e["to_bus"], flow_mw=float(flow),
            rating_mva=rating if usable else None,
            loading_pct=abs(float(flow)) / rating * 100 if usable else None,
        ))
        net_from_flows[e["from_bus"]] += float(flow)
        net_from_flows[e["to_bus"]] -= float(flow)

    adjusted_injections = dict(injections)
    for island in island_info:
        adjusted_injections[island["slack_bus"]] = (
            adjusted_injections.get(island["slack_bus"], 0.0) - island["imbalance_mw"]
        )
    max_kcl_residual = max(
        (abs(net_from_flows[n] - adjusted_injections.get(n, 0.0)) for n in nodes),
        default=0.0,
    )
    energized = [
        island for island in island_info
        if not island["external_dc_boundary"]
        if island["bus_count"] > 1 or abs(island["imbalance_mw"]) > 1e-6
    ]
    status = "islanded" if len(energized) > 1 else "ok"
    reason = (
        "One or more disconnected components have no online generator; their slack is virtual."
        if any(
            not island["external_dc_boundary"]
            and not island["has_generator"] and abs(island["imbalance_mw"]) > 1e-6
            for island in island_info
        )
        else None
    )
    return dict(
        status=status, reason=reason, flows=flows,
        bus_angles_rad={bus: angle[bus] for bus in sorted(active_buses)},
        balance_mw=raw_balance, islands=island_info,
        max_kcl_residual_mw=max_kcl_residual,
        disabled_branches=sorted(disabled_branches),
        disabled_transformers=sorted(disabled_transformers),
        dc_transfers_mw=applied_dc_transfers,
    )
