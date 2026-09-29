"""Run an auditable local planning-case evaluation from a JSON request.

The built-in example is synthetic. It demonstrates the calculation path on the
real TYTFS case without claiming current grid conditions or a reviewed action.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.network import load_case
from backend.app.network_forecast import (
    DEFAULT_CASE_DIR, DEFAULT_CROSSWALK_PATH, DEFAULT_PLANNED_OUTAGE,
    load_reviewed_crosswalk,
)
from backend.app.operator_evaluation import OperatorEvaluationRequest, evaluate_operator_case


def example_request() -> dict:
    as_of = datetime(2026, 9, 28, 23, 45, tzinfo=timezone.utc)
    start = datetime(2026, 9, 29, tzinfo=timezone.utc)
    issue = "2026-09-28T23:30:00Z"
    available = "2026-09-28T23:40:00Z"
    rows = []
    evidence = []
    for index in range(48):
        valid = (start + timedelta(minutes=30 * index)).isoformat().replace("+00:00", "Z")
        rows.append({
            "issue_time": issue, "forecast_source": "synthetic TYTFS planning example",
            "valid_time": valid, "demand_mw": 3402.3,
            "constraint_probability": 0.5, "expected_constraint_mwh": 20.0,
            "forecast_confidence": 0.5,
            "regional_generation_mw": {"F:Ballylickey": {"wind": 20.0}},
            "recoverable_renewable_mw": {"F:Ballylickey": {"wind": 10.0}},
            "drivers": ["synthetic values for planning-path demonstration"],
        })
        for field, value in (("constraint_mwh", 20.0), ("curtailment_mwh", 5.0)):
            evidence.append({
                "field": field, "value": value, "unit": "MWh per half-hour",
                "source_type": "forecast", "source": "synthetic TYTFS planning example",
                "source_version": "example-1", "available_at": available,
                "issued_at": issue, "valid_at": valid, "max_age_seconds": 3600,
                "limitation": "Invented scenario value; no operational forecast or observed outcome.",
            })
    actions = []
    for power in (10.0, 5.0):
        actions.append({
            "action_id": f"illustrative-flex-{int(power)}mw",
            "load_bus_id": 2221, "renewable_bus_id": 1281,
            "allocation_region": "F:Ballylickey", "generation_type": "wind",
            "power_mw": power, "available_from": "2026-09-29T00:00:00Z",
            "available_until": "2026-09-29T01:00:00Z",
            "review_status": "scenario_assumption",
            "evidence_reference": "hypothetical demand at Dunmanway 110 kV; no flexible asset verified",
        })
    return {
        "decision_case": {
            "case_id": "synthetic-tytfs-planning-example",
            "scenario_ids": ["local_constraint"],
            "location": "F:Ballylickey to Dunmanway station proxy",
            "asset_ids": ["1281", "2221"],
            "as_of": as_of.isoformat(), "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=24)).isoformat(),
        },
        "forecast_available_at": available,
        "forecast_version": "synthetic-example-1",
        "forecast_evidence_reference": "invented conditions in scripts/run_operator_evaluation.py",
        "forecast_rows": rows, "action_candidates": actions, "evidence": evidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--request", type=Path, help="JSON decision/forecast/action request")
    source.add_argument("--example", action="store_true", help="run a clearly synthetic TYTFS example")
    parser.add_argument("--output", type=Path, required=True, help="write complete JSON result")
    args = parser.parse_args()
    payload = example_request() if args.example else json.loads(args.request.read_text())
    request = OperatorEvaluationRequest.model_validate(payload)
    result = evaluate_operator_case(
        request, load_case(DEFAULT_CASE_DIR),
        load_reviewed_crosswalk(DEFAULT_CROSSWALK_PATH),
        planned_outage=DEFAULT_PLANNED_OUTAGE,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if args.example:
        request_path = args.output.with_name(args.output.stem + ".request.json")
        request_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
        print(f"Synthetic example request: {request_path}")
    print(f"Evaluation result: {args.output}")
    print(json.dumps({
        "case_id": result["case_id"],
        "current_plan_expected_dispatch_down_mwh": result["current_plan"]["expected_dispatch_down_mwh"],
        "action_bounds": result["ranked_modeled_capture_bounds"],
        "avoided_dispatch_down_ranking": result["ranked_expected_avoided_dispatch_down"],
        "recommendation": result["recommendation"],
        "blocking_reasons": result["blocking_reasons"],
    }, indent=2))


if __name__ == "__main__":
    main()
