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
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

RAW_MEMBER = "TYTFS2024_studyfiles/TYTFS2024_SV2024_V33.raw"
SOURCE_URL = "https://cms.eirgrid.ie/sites/default/files/publications/TYTFS2024_studyfiles.zip"

BUS_COLUMNS = ("bus_id", "name", "base_kv", "bus_type", "in_service", "vm_pu", "va_deg")
BRANCH_COLUMNS = ("asset_id", "from_bus", "to_bus", "circuit_id", "r_pu", "x_pu", "rate_a_mva", "rate_b_mva", "rate_c_mva", "in_service")
TRANSFORMER_COLUMNS = ("transformer_id", "from_bus", "to_bus", "third_bus", "circuit_id", "r_pu", "x_pu", "x23_pu", "x31_pu", "tap_ratio", "phase_shift_deg", "rate_a_mva", "rate_b_mva", "rate_c_mva", "in_service")
GENERATOR_COLUMNS = ("bus_id", "generator_id", "pg_mw", "pmax_mw", "pmin_mw", "in_service")
LOAD_COLUMNS = ("bus_id", "load_id", "p_mw", "in_service")


@dataclass(frozen=True)
class NetworkCase:
    buses: list[dict]
    branches: list[dict]
    transformers: list[dict]
    generators: list[dict]
    loads: list[dict]
    metadata: dict


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


def parse_raw(raw: bytes) -> NetworkCase:
    """Parse the 2024 summer V33 case without changing its source statuses."""
    text = raw.decode("utf-8-sig")
    if "SUMMER 01/07/2024" not in text.splitlines()[1]:
        raise ValueError("Expected the TYTFS summer 1 July 2024 case")
    parts = _sections(text)
    buses = []
    for line in parts["buses"]:
        f = _fields(line)
        buses.append(dict(bus_id=int(f[0]), name=f[1], base_kv=_number(f[2]), bus_type=int(f[3]), in_service=int(f[3]) != 4, vm_pu=_number(f[7]), va_deg=_number(f[8])))
    loads = []
    for line in parts["loads"]:
        f = _fields(line)
        # RAW load PL is followed by constant-current and constant-admittance
        # terms. Those terms are retained in the metadata warning, not DC P.
        loads.append(dict(bus_id=int(f[0]), load_id=f[1], p_mw=_number(f[5]), in_service=int(f[2]) == 1))
    generators = []
    for line in parts["generators"]:
        f = _fields(line)
        generators.append(dict(bus_id=int(f[0]), generator_id=f[1], pg_mw=_number(f[2]), pmax_mw=_number(f[16]), pmin_mw=_number(f[17]), in_service=int(f[14]) == 1))
    branches = []
    for line in parts["branches"]:
        f = _fields(line)
        i, j = int(f[0]), int(f[1])
        branches.append(dict(asset_id=_asset_id(i, j, None, f[2]), from_bus=i, to_bus=j, circuit_id=f[2], r_pu=_number(f[3]), x_pu=_number(f[4]), rate_a_mva=_number(f[6]), rate_b_mva=_number(f[7]), rate_c_mva=_number(f[8]), in_service=int(f[13]) == 1))
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
        winding = _fields(tlines[offset + 2])
        second = _fields(tlines[offset + 3])
        if int(a[4]) != 1 or int(a[5]) not in (1, 2):
            raise ValueError("Unsupported transformer CW/CZ unit code")
        impedance_scale = 100.0 / _number(z[2]) if int(a[5]) == 2 else 1.0
        tap = _number(winding[0]) / _number(second[0])
        transformers.append(dict(transformer_id=_asset_id(i, j, k, a[3]), from_bus=i, to_bus=j, third_bus=k or "", circuit_id=a[3], r_pu=_number(z[0]) * impedance_scale, x_pu=_number(z[1]) * impedance_scale, x23_pu=_number(z[4]) if k else "", x31_pu=_number(z[7]) if k else "", tap_ratio=tap, phase_shift_deg=_number(winding[2]), rate_a_mva=_number(winding[3]), rate_b_mva=_number(winding[4]), rate_c_mva=_number(winding[5]), in_service=int(a[11]) == 1))
        offset += length
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
    metadata = dict(source_url=SOURCE_URL, source_member=RAW_MEMBER, source_sha256=hashlib.sha256(raw).hexdigest(), season="summer", study_year=2024, scenario_date="2024-07-01", pss_e_version=33, base_mva=100.0, scenario_label="TYTFS 2024 planning scenario", source_note="Reference planning power flow; not a live operational state.")
    return NetworkCase(buses, branches, transformers, generators, loads, metadata)


def import_zip(path: str | Path) -> NetworkCase:
    with zipfile.ZipFile(path) as archive:
        return parse_raw(archive.read(RAW_MEMBER))


def write_case(case: NetworkCase, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for filename, rows, columns in (("buses.csv", case.buses, BUS_COLUMNS), ("branches.csv", case.branches, BRANCH_COLUMNS), ("transformers.csv", case.transformers, TRANSFORMER_COLUMNS), ("generators.csv", case.generators, GENERATOR_COLUMNS), ("loads.csv", case.loads, LOAD_COLUMNS)):
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
                if row[key] != "": row[key] = int(row[key])
            for key in floats:
                if row[key] != "": row[key] = float(row[key])
            row["in_service"] = row["in_service"] == "True"
        return rows
    buses = read("buses.csv", {"bus_id", "bus_type"}, {"base_kv", "vm_pu", "va_deg"})
    branches = read("branches.csv", {"from_bus", "to_bus"}, {"r_pu", "x_pu", "rate_a_mva", "rate_b_mva", "rate_c_mva"})
    transformers = read("transformers.csv", {"from_bus", "to_bus"}, {"r_pu", "x_pu", "x23_pu", "x31_pu", "tap_ratio", "phase_shift_deg", "rate_a_mva", "rate_b_mva", "rate_c_mva"})
    for t in transformers:
        if t["third_bus"] != "": t["third_bus"] = int(t["third_bus"])
    generators = read("generators.csv", {"bus_id"}, {"pg_mw", "pmax_mw", "pmin_mw"})
    loads = read("loads.csv", {"bus_id"}, {"p_mw"})
    return NetworkCase(buses, branches, transformers, generators, loads, json.loads((directory / "provenance.json").read_text()))


def _edges(case: NetworkCase, disabled_branches: set[str], disabled_transformers: set[str]) -> list[dict]:
    active_buses = {b["bus_id"] for b in case.buses if b["in_service"]}
    edges = []
    for b in case.branches:
        if b["in_service"] and b["asset_id"] not in disabled_branches and {b["from_bus"], b["to_bus"]} <= active_buses:
            edges.append(dict(asset_type="branch", asset_id=b["asset_id"], from_bus=b["from_bus"], to_bus=b["to_bus"], x_pu=b["x_pu"], tap_ratio=1.0, phase_shift_deg=0.0, rating_mva=b["rate_a_mva"]))
    for t in case.transformers:
        if not t["in_service"] or t["transformer_id"] in disabled_transformers:
            continue
        terminals = [t["from_bus"], t["to_bus"]] + ([t["third_bus"]] if t["third_bus"] else [])
        if not set(terminals) <= active_buses:
            continue
        if not t["third_bus"]:
            edges.append(dict(asset_type="transformer", asset_id=t["transformer_id"], from_bus=t["from_bus"], to_bus=t["to_bus"], x_pu=t["x_pu"], tap_ratio=t["tap_ratio"], phase_shift_deg=t["phase_shift_deg"], rating_mva=t["rate_a_mva"]))
        else:
            x12, x23, x31 = t["x_pu"], t["x23_pu"], t["x31_pu"]
            xs = ((x12 + x31 - x23) / 2, (x12 + x23 - x31) / 2, (x23 + x31 - x12) / 2)
            star = -len(edges) - 1  # stable within this solve; never a real RAW bus
            for winding, (bus, x) in enumerate(zip(terminals, xs), 1):
                # A star leg can have zero or negative reactance even when all
                # three measured pair impedances are positive. A zero leg is
                # approximated by a very small series reactance.
                edges.append(dict(asset_type="transformer", asset_id=f"{t['transformer_id']}/w{winding}", from_bus=bus, to_bus=star, x_pu=x if abs(x) > 1e-8 else 1e-8, tap_ratio=t["tap_ratio"] if winding == 1 else 1.0, phase_shift_deg=t["phase_shift_deg"] if winding == 1 else 0.0, rating_mva=t["rate_a_mva"] if winding == 1 else None))
    return edges


def solve_dc_case(case: NetworkCase, *, disabled_branches: Iterable[str] = (), disabled_transformers: Iterable[str] = (), injection_overrides_mw: Mapping[int, float] | None = None) -> dict:
    """Solve fixed MW injections by component, assigning residual to one slack bus.

    `injection_overrides_mw` replaces net PG minus load at named source buses.
    Disabling a three-winding transformer removes all three windings. Ratings
    are MVA; loading_pct is only a DC MW/MVA proxy.
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
    edges = _edges(case, disabled_branches, disabled_transformers)
    nodes = set(active_buses)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in edges:
        i, j = edge["from_bus"], edge["to_bus"]
        if not edge["x_pu"]:
            return dict(status="unsolved", reason=f"Zero reactance on {edge['asset_id']}", flows=[], bus_angles_rad={}, balance_mw=0.0, islands=[])
        nodes.update((i, j)); adjacency[i].add(j); adjacency[j].add(i)
    injections = defaultdict(float)
    for g in case.generators:
        if g["in_service"] and g["bus_id"] in active_buses: injections[g["bus_id"]] += g["pg_mw"]
    for load in case.loads:
        if load["in_service"] and load["bus_id"] in active_buses: injections[load["bus_id"]] -= load["p_mw"]
    injections.update(overrides)
    raw_balance = sum(injections.values())
    components = []
    remaining = set(nodes)
    while remaining:
        seed = min(remaining); found = {seed}; queue = deque([seed]); remaining.remove(seed)
        while queue:
            for neighbor in adjacency[queue.popleft()] & remaining:
                found.add(neighbor); remaining.remove(neighbor); queue.append(neighbor)
        components.append(found)
    slack_candidates = {b["bus_id"] for b in case.buses if b["bus_type"] == 3 and b["in_service"]}
    generator_buses = {g["bus_id"] for g in case.generators if g["in_service"]}
    angle: dict[int, float] = {}
    island_info = []
    for component in components:
        real = component & active_buses
        if not real:
            continue
        candidates = component & slack_candidates or component & generator_buses
        slack = min(candidates) if candidates else min(real)
        imbalance = sum(injections[n] for n in component)
        island_info.append(dict(bus_count=len(real), slack_bus=slack, imbalance_mw=imbalance, has_generator=bool(component & generator_buses)))
        comp_edges = [e for e in edges if e["from_bus"] in component]
        ordered = sorted(component); index = {bus: position for position, bus in enumerate(ordered)}
        row, col, vals = [], [], []
        rhs = np.array([injections[n] for n in ordered], dtype=float)
        rhs[index[slack]] -= imbalance
        for e in comp_edges:
            i, j = index[e["from_bus"]], index[e["to_bus"]]
            b = case.metadata["base_mva"] / (e["x_pu"] * e["tap_ratio"])
            for r, c, v in ((i,i,b),(j,j,b),(i,j,-b),(j,i,-b)):
                row.append(r); col.append(c); vals.append(v)
            shift = math.radians(e["phase_shift_deg"])
            rhs[i] += b * shift; rhs[j] -= b * shift
        if len(ordered) == 1:
            solution = np.array([0.0])
        else:
            matrix = coo_matrix((vals, (row, col)), shape=(len(ordered),len(ordered))).tocsr()
            keep = [n for n in range(len(ordered)) if n != index[slack]]
            try:
                solution = np.zeros(len(ordered))
                solution[keep] = spsolve(matrix[keep][:,keep], rhs[keep])
            except Exception as exc:
                return dict(status="unsolved", reason=str(exc), flows=[], bus_angles_rad={}, balance_mw=raw_balance, islands=island_info)
            if not np.all(np.isfinite(solution)):
                return dict(status="unsolved", reason="Singular DC matrix", flows=[], bus_angles_rad={}, balance_mw=raw_balance, islands=island_info)
        angle.update(zip(ordered, map(float, solution)))
    flows = []
    net_from_flows = defaultdict(float)
    for e in edges:
        b = case.metadata["base_mva"] / (e["x_pu"] * e["tap_ratio"])
        flow = b * (angle[e["from_bus"]] - angle[e["to_bus"]] - math.radians(e["phase_shift_deg"]))
        rating = e["rating_mva"]
        # 0 and 9999 MVA are absent/placeholder ratings in this RAW case.
        usable = rating is not None and 0 < rating < 9000
        flows.append(dict(asset_type=e["asset_type"], asset_id=e["asset_id"], from_bus=e["from_bus"], to_bus=e["to_bus"], flow_mw=float(flow), rating_mva=rating if usable else None, loading_pct=abs(float(flow)) / rating * 100 if usable else None))
        net_from_flows[e["from_bus"]] += float(flow)
        net_from_flows[e["to_bus"]] -= float(flow)
    adjusted_injections = dict(injections)
    for island in island_info:
        adjusted_injections[island["slack_bus"]] = adjusted_injections.get(island["slack_bus"], 0.0) - island["imbalance_mw"]
    max_kcl_residual = max((abs(net_from_flows[n] - adjusted_injections.get(n, 0.0)) for n in nodes), default=0.0)
    energized = [island for island in island_info if island["bus_count"] > 1 or abs(island["imbalance_mw"]) > 1e-6]
    status = "islanded" if len(energized) > 1 else "ok"
    reason = "One or more disconnected components have no online generator; their slack is virtual." if any(not island["has_generator"] and abs(island["imbalance_mw"]) > 1e-6 for island in island_info) else None
    return dict(status=status, reason=reason, flows=flows, bus_angles_rad={bus: angle[bus] for bus in sorted(active_buses)}, balance_mw=raw_balance, islands=island_info, max_kcl_residual_mw=max_kcl_residual, disabled_branches=sorted(disabled_branches), disabled_transformers=sorted(disabled_transformers))
