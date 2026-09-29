"""Append-only case records and deterministic, explainable comparison search."""

from __future__ import annotations

from datetime import datetime
import fcntl
import json
from pathlib import Path

from .contracts import Contract, DecisionCase, PastCase, utc

DEMO_CASES = Path(__file__).with_name("demo_cases.jsonl")


class ComparableCase(Contract):
    record: PastCase
    reason: str


def load_cases(path: Path = DEMO_CASES) -> list[PastCase]:
    if not path.exists():
        return []
    return [PastCase.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]


def append_case(path: Path, record: PastCase) -> None:
    """Append without replacing previous evidence, even across concurrent writers."""
    record = PastCase.model_validate(record.model_dump())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            stream.seek(0)
            existing = [PastCase.model_validate_json(line) for line in stream if line.strip()]
            if any(item.record_id == record.record_id for item in existing):
                raise ValueError(f"case record {record.record_id} already exists")
            stream.seek(0, 2)
            stream.write(json.dumps(record.model_dump(mode="json"), sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _condition_matches(query: dict[str, float | str], past: dict[str, float | str]) -> list[str]:
    matches: list[str] = []
    for key, value in query.items():
        candidate = past.get(key)
        if isinstance(value, (float, int)) and isinstance(candidate, (float, int)):
            if abs(float(value) - float(candidate)) <= 0.2 * max(abs(float(value)), 1.0):
                matches.append(key)
        elif candidate == value:
            matches.append(key)
    return matches


def search_cases(
    records: list[PastCase],
    case: DecisionCase,
    *,
    conditions: dict[str, float | str] | None = None,
    minimum_quality: str = "low",
    limit: int = 5,
) -> list[ComparableCase]:
    """Use only records knowable by as_of and explain each comparison."""
    quality = {"low": 0, "medium": 1, "high": 2}
    if minimum_quality not in quality or limit < 1:
        raise ValueError("invalid quality floor or result limit")
    query = conditions or {}
    eligible = [record for record in records
                if utc(record.available_at) <= utc(case.as_of)
                and set(record.scenario_ids).intersection(case.scenario_ids)
                and quality[record.quality] >= quality[minimum_quality]]

    def key(record: PastCase):
        matched = _condition_matches(query, record.conditions)
        same_location = bool(case.location and record.location == case.location)
        return (-int(same_location), -len(matched), -quality[record.quality],
                -utc(record.starts_at).timestamp(), record.record_id)

    output = []
    for record in sorted(eligible, key=key)[:limit]:
        matched = _condition_matches(query, record.conditions)
        reasons = ["shared scenario"]
        if case.location and record.location == case.location:
            reasons.append("same location")
        if matched:
            reasons.append("similar " + ", ".join(sorted(matched)))
        reasons.append(f"{record.quality}-quality {record.outcome_label} outcome")
        output.append(ComparableCase(record=record, reason="; ".join(reasons)))
    return output
