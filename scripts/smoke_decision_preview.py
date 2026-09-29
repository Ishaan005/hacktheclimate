"""Exercise the advisory case preview without a running server or live credentials."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app


def main() -> None:
    as_of = datetime.now(timezone.utc)
    start = as_of.replace(second=0, microsecond=0, minute=30 if as_of.minute >= 30 else 0) + timedelta(minutes=30)
    response = TestClient(app).post("/v1/decision/preview", json={
        "case": {
            "case_id": f"illustrative-{uuid4()}",
            "scenario_ids": ["illustrative-local-constraint"],
            "location": "illustrative-location",
            "asset_ids": [],
            "as_of": as_of.isoformat(),
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=24)).isoformat(),
            "existing_instructions": [],
        },
    })
    response.raise_for_status()
    result = response.json()
    print(json.dumps({
        "contract_status": result["contract_status"],
        "source_status": result["sources"][0]["status"],
        "evidence_coverage": result["evidence_coverage"],
        "expected_constraint_mwh": result["current_plan"]["expected_constraint_mwh"],
        "expected_dispatch_down_mwh": result["current_plan"]["expected_dispatch_down_mwh"],
        "safety": result["current_plan"]["safety"]["overall"],
        "blocking_reasons": result["blocking_reasons"],
        "recommendation": result["recommendation"],
    }, indent=2))


if __name__ == "__main__":
    main()
