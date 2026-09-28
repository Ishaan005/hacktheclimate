from backend.app.dispatch_down.predictor import get_dispatch_down_predictor


def test_predicts_one_hour_ahead_historical_dispatch_down():
    result = get_dispatch_down_predictor().predict("2026-01-24T01:00:00Z")

    assert result["mode"] == "historical_replay"
    assert result["horizon_hours"] == 1
    assert result["risk"] in {"low", "elevated", "high"}
    assert 0.0 <= result["event_probability"] <= 1.0
    assert result["expected_dispatch_down_mwh"] >= 0.0


def test_predicts_a_full_replay_day():
    predictor = get_dispatch_down_predictor()
    result = predictor.predict_day("2026-01-24T01:00:00Z")

    assert result["date"] == "2026-01-24"
    assert len(result["points"]) == 48
    single = predictor.predict("2026-01-24T01:00:00Z")
    match = next(p for p in result["points"] if p["target_timestamp"] == "2026-01-24T01:00:00")
    assert abs(match["event_probability"] - single["event_probability"]) < 1e-9
    assert abs(match["expected_dispatch_down_mwh"] - single["expected_dispatch_down_mwh"]) < 1e-9
