import pytest
from fastapi.testclient import TestClient

from backend.app.constraints.checker import get_constraint_checker, risk_level
from backend.app.main import app

client = TestClient(app)


def test_utc_suffix_and_naive_times_give_the_same_replay():
    checker = get_constraint_checker()
    with_z = checker.check("2026-01-24T01:00:00Z", 1)
    naive = checker.check("2026-01-24T01:00:00", 1)
    offset = checker.check("2026-01-24T02:00:00+01:00", 1)
    assert with_z == naive == offset
    assert with_z["target"] == "constraint_mwh"
    assert with_z["risk_level"] in {"low", "elevated", "high"}
    assert 0.0 <= with_z["event_probability"] <= 1.0
    assert with_z["interval_80_mwh"]["low"] <= with_z["interval_80_mwh"]["high"]


@pytest.mark.parametrize("horizon", [1, 4, 6, 12, 24])
def test_every_supported_horizon_loads(horizon):
    result = get_constraint_checker().check("2026-05-10T12:00:00Z", horizon)
    assert result["horizon_hours"] == horizon


def test_risk_bands_match_dispatch_down():
    assert [risk_level(p) for p in (0.1, 0.3, 0.69, 0.7)] == ["low", "elevated", "elevated", "high"]


def test_route_explains_bad_requests():
    ok = client.get("/v1/constraints/check", params={"timestamp": "2026-01-24T01:00:00Z"})
    assert ok.status_code == 200
    outside = client.get("/v1/constraints/check", params={"timestamp": "2027-01-01T00:00:00Z"})
    assert outside.status_code == 422 and "Available:" in outside.json()["detail"]
    horizon = client.get("/v1/constraints/check", params={"timestamp": "2026-01-24T01:00:00Z", "horizon_hours": 2})
    assert horizon.status_code == 422
