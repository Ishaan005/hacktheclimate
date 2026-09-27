from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.demo import AbsorptionRequest, AssetSpec, demo_absorption


def test_retrospective_demo_respects_energy_and_interval_limits():
    result = demo_absorption(
        AbsorptionRequest(
            start_target="2026-01-24T00:00:00Z",
            intervals=4,
            assets=[
                AssetSpec(
                    name="flexible_load",
                    max_power_mw=10,
                    energy_required_mwh=8,
                    available=[True, False, True, True],
                )
            ],
        )
    )

    rows = result["intervals"]
    powers = result["schedule"]["schedule_mw"]["flexible_load"]
    assert result["scenario"] == "retrospective_1h_operational"
    assert len(rows) == len(powers) == 4
    assert rows[0]["input_timestamp"] == "2026-01-23T23:00:00"
    assert rows[0]["target_timestamp"] == "2026-01-24T00:00:00"
    assert powers[1] == 0
    assert all(0 <= power <= 10 for power in powers)
    assert sum(powers) * 0.5 <= 8.001
    assert all(power * 0.5 <= row["predicted_dispatch_down_mwh"] + 0.001 for power, row in zip(powers, rows))
    assert result["schedule"]["absorbed_mwh"] <= result["predicted_dispatch_down_mwh"]


def test_retrospective_demo_rejects_invalid_window():
    request = AbsorptionRequest(
        start_target="2026-02-01T00:00:00Z",
        intervals=1,
        assets=[AssetSpec(name="load", max_power_mw=1, energy_required_mwh=1, available=[True])],
    )
    with pytest.raises(HTTPException) as exc:
        demo_absorption(request)
    assert exc.value.status_code == 422
