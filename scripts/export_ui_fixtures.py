"""Export response examples from the included data and model artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.encoders import jsonable_encoder

from backend.app.demo import AbsorptionRequest, demo_absorption
from backend.app.main import health, sample_dispatch_down, sample_pressure
from backend.app.network import NetworkCase
from backend.app.network_forecast import build_network_forecast
from backend.app.network_scenarios import Asset

OUTPUT = Path("docs/ui-handoff")
REQUEST = {
    "start_target": "2026-01-24T00:00:00Z",
    "intervals": 4,
    "assets": [{
        "name": "flexible_load",
        "max_power_mw": 10,
        "energy_required_mwh": 8,
        "available": [True, False, True, True],
    }],
}


def save(name: str, data: object) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(
        json.dumps(jsonable_encoder(data), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def synthetic_network_response() -> list[dict]:
    """Contract-only example using a four-bus test grid and invented inputs."""
    case = NetworkCase(
        buses=[
            {"bus_id": bus, "bus_type": 3 if bus == 1 else 1, "in_service": True}
            for bus in (1, 2, 3, 4)
        ],
        branches=[
            {"asset_id": f"{i}:{j}:1", "from_bus": i, "to_bus": j,
             "x_pu": 0.1, "rate_a_mva": 100.0, "in_service": True}
            for i, j in ((1, 2), (2, 4), (1, 3), (3, 4), (2, 3))
        ],
        transformers=[],
        generators=[
            {"bus_id": 1, "pg_mw": 100.0, "pmax_mw": 200.0, "pmin_mw": 0.0, "in_service": True},
            {"bus_id": 2, "pg_mw": 0.0, "pmax_mw": 80.0, "pmin_mw": 0.0, "in_service": True},
        ],
        loads=[{"bus_id": 4, "p_mw": 100.0, "in_service": True}],
        metadata={"base_mva": 100.0},
    )
    crosswalk = [{
        "allocation_region": "Synthetic South-West",
        "generation_type": "wind",
        "bus_id": 2,
        "mec_mw": 80.0,
        "review_status": "accepted_verified",
        "connection_status": "connected",
    }]
    start = datetime(2026, 9, 29, tzinfo=timezone.utc)
    rows = [{
        "issue_time": "2026-09-28T18:00:00Z",
        "forecast_source": "synthetic-ui-contract-example",
        "valid_time": (start + timedelta(minutes=30 * i)).isoformat().replace("+00:00", "Z"),
        "constraint_probability": 0.65,
        "expected_constraint_mwh": 20.0,
        "forecast_confidence": 0.75,
        "demand_mw": 100.0,
        "regional_generation_mw": {"Synthetic South-West": {"wind": 40.0}},
        "dc_transfers_mw": {},
        "drivers": ["invented UI example"],
    } for i in range(48)]
    return build_network_forecast(
        case, rows, crosswalk, planned_outage=Asset("branch", "1:3:1"),
        contingency_candidates=3,
    )


def main() -> None:
    save("health.response.json", health())
    save("pressure.response.json", sample_pressure(limit=96))
    save("dispatch-down.response.json", sample_dispatch_down(limit=96))
    save("absorption.request.json", REQUEST)
    save("absorption.response.json", demo_absorption(AbsorptionRequest.model_validate(REQUEST)))
    save("network.synthetic.response.json", synthetic_network_response())


if __name__ == "__main__":
    main()
