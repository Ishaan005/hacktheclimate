import hashlib

import pytest
from openpyxl import Workbook

from scripts.network_generators import allocate, build_crosswalk, write_csv, PROJECT_FIELDS


def fixture_files(tmp_path):
    book = Workbook()
    sheet = book.active
    sheet.title = "RES & Battery Generation Table"
    sheet.append([None])
    sheet.append([None])
    sheet.append([None])
    sheet.append(["Name", "Area", "Node", "Generation", "System", "Connection", "Processing", "Maximum Export"])
    sheet.append([None, None, None, "Type", "Operator", "Status", "Type", "Capacity (MW)"])
    sheet.append(["One", "R1", "Alpha", "wind", "DSO", "connected", "Gate", 10])
    sheet.append(["Two", "R1", "Alpha", "wind", "TSO", "connected", "Gate", 30])
    sheet.append(["Future", "R1", "Alpha", "wind", "DSO", "due to connected", "Gate", 100])
    sheet.append(["Unknown", "R2", "Missing", "solar", "DSO", "connected", "Gate", 5])
    workbook = tmp_path / "projects.xlsx"
    book.save(workbook)
    buses = tmp_path / "buses.csv"
    write_csv(buses, ["bus_id", "name", "base_kv"], [
        {"bus_id": "1", "name": "ALPHA", "base_kv": 110},
        {"bus_id": "2", "name": "ALPHA", "base_kv": 38},
        {"bus_id": "3", "name": "BETA", "base_kv": 110},
    ])
    return workbook, buses


def test_crosswalk_keeps_name_matches_unaccepted_and_future_separate(tmp_path):
    workbook, buses = fixture_files(tmp_path)
    rows, summary = build_crosswalk(workbook, buses)
    assert len(rows) == 4
    assert [row["review_status"] for row in rows] == ["ambiguous", "ambiguous", "ambiguous", "unmatched"]
    assert rows[0]["candidate_bus_ids"] == "1|2"
    assert rows[0]["bus_id"] == ""
    assert summary["by_status"]["connected"]["ambiguous"] == {"rows": 2, "mec_mw": 40.0}
    assert summary["by_status"]["connected"]["unmatched"] == {"rows": 1, "mec_mw": 5.0}
    assert summary["by_status"]["due to connected"]["total"] == {"rows": 1, "mec_mw": 100.0}


def test_reviewed_proxy_allocates_and_reconciles_without_future_capacity(tmp_path):
    workbook, buses = fixture_files(tmp_path)
    digest = hashlib.sha256(workbook.read_bytes()).hexdigest()
    reviews = tmp_path / "reviews.csv"
    write_csv(reviews, ["source_row", "workbook_sha256", "bus_id", "bus_name", "bus_base_kv",
                        "review_status", "allocation_region", "review_evidence", "override_reason"], [
        {"source_row": str(row), "workbook_sha256": digest, "bus_id": "1", "bus_name": "ALPHA",
         "bus_base_kv": 110, "review_status": "accepted_proxy", "allocation_region": "R1:Alpha",
         "review_evidence": "checked interface proxy", "override_reason": ""}
        for row in (6, 7)
    ])
    rows, summary = build_crosswalk(workbook, buses, reviews)
    assert summary["by_status"]["connected"]["accepted_proxy"] == {"rows": 2, "mec_mw": 40.0}
    assert summary["by_status"]["due to connected"]["accepted_proxy"]["rows"] == 0
    crosswalk = tmp_path / "crosswalk.csv"
    write_csv(crosswalk, PROJECT_FIELDS, rows)
    forecast = tmp_path / "forecast.csv"
    write_csv(forecast, ["allocation_region", "generation_type", "forecast_mw"], [
        {"allocation_region": "R1:Alpha", "generation_type": "wind", "forecast_mw": 20}
    ])
    weights = tmp_path / "weights.csv"
    write_csv(weights, ["bus_id", "weight"], [{"bus_id": "1", "weight": 1}, {"bus_id": "3", "weight": 3}])
    allocation, report = allocate(crosswalk, forecast, weights, 80, buses)
    by_bus = {row["bus_id"]: row for row in allocation}
    assert by_bus["1"]["wind_mw"] == pytest.approx(20)
    assert by_bus["1"]["load_mw"] == pytest.approx(20)
    assert by_bus["3"]["load_mw"] == pytest.approx(60)
    assert report["allocated_mw"] == {"wind_mw": 20.0, "solar_mw": 0.0, "load_mw": 80.0}
    assert report["net_injection_mw"] == pytest.approx(-60)


def test_rejects_stale_review_and_unplaced_forecast(tmp_path):
    workbook, buses = fixture_files(tmp_path)
    reviews = tmp_path / "reviews.csv"
    write_csv(reviews, ["source_row", "workbook_sha256"], [{"source_row": "6", "workbook_sha256": "stale"}])
    with pytest.raises(ValueError, match="another ECP workbook"):
        build_crosswalk(workbook, buses, reviews)
    rows, _ = build_crosswalk(workbook, buses)
    crosswalk = tmp_path / "crosswalk.csv"
    write_csv(crosswalk, PROJECT_FIELDS, rows)
    forecast = tmp_path / "forecast.csv"
    write_csv(forecast, ["allocation_region", "generation_type", "forecast_mw"], [
        {"allocation_region": "R1", "generation_type": "wind", "forecast_mw": 20}
    ])
    weights = tmp_path / "weights.csv"
    write_csv(weights, ["bus_id", "weight"], [{"bus_id": "1", "weight": 1}])
    with pytest.raises(ValueError, match="no reviewed connected sites"):
        allocate(crosswalk, forecast, weights, 80, buses)


def test_future_review_is_forbidden_and_partial_group_cannot_absorb_forecast(tmp_path):
    workbook, buses = fixture_files(tmp_path)
    digest = hashlib.sha256(workbook.read_bytes()).hexdigest()
    reviews = tmp_path / "reviews.csv"
    fields = ["source_row", "workbook_sha256", "bus_id", "bus_name", "bus_base_kv",
              "review_status", "allocation_region", "review_evidence", "override_reason"]
    review = {"source_row": "8", "workbook_sha256": digest, "bus_id": "1", "bus_name": "ALPHA",
              "bus_base_kv": 110, "review_status": "accepted_proxy", "allocation_region": "R1",
              "review_evidence": "checked", "override_reason": ""}
    write_csv(reviews, fields, [review])
    with pytest.raises(ValueError, match="future row"):
        build_crosswalk(workbook, buses, reviews)
    review["source_row"] = "6"
    write_csv(reviews, fields, [review])
    rows, _ = build_crosswalk(workbook, buses, reviews)
    crosswalk = tmp_path / "crosswalk.csv"
    write_csv(crosswalk, PROJECT_FIELDS, rows)
    forecast = tmp_path / "forecast.csv"
    write_csv(forecast, ["allocation_region", "generation_type", "forecast_mw"], [
        {"allocation_region": "R1", "generation_type": "wind", "forecast_mw": 5}
    ])
    loads = tmp_path / "loads.csv"
    write_csv(loads, ["bus_id", "load_id", "p_mw", "in_service"], [
        {"bus_id": "1", "load_id": "A", "p_mw": 10, "in_service": "true"},
        {"bus_id": "1", "load_id": "B", "p_mw": 5, "in_service": "true"},
        {"bus_id": "3", "load_id": "C", "p_mw": 100, "in_service": "false"},
    ])
    with pytest.raises(ValueError, match="unreviewed connected sites"):
        allocate(crosswalk, forecast, loads, 30, buses)
    rows[1]["review_status"] = "accepted_proxy"
    rows[1]["bus_id"] = "1"
    write_csv(crosswalk, PROJECT_FIELDS, rows)
    allocation, report = allocate(crosswalk, forecast, loads, 30, buses)
    assert report["load_weight_total"] == 15
    assert allocation[0]["load_mw"] == pytest.approx(30)
    write_csv(forecast, ["allocation_region", "generation_type", "forecast_mw"], [
        {"allocation_region": "R1", "generation_type": "wind", "forecast_mw": 50}
    ])
    with pytest.raises(ValueError, match="exceeds reviewed MEC"):
        allocate(crosswalk, forecast, loads, 30, buses)
