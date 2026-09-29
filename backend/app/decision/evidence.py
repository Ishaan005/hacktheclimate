"""Resolve source values as they were knowable at a case decision time."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from backend.app.gfs_forecast import validate_snapshot

from .contracts import DecisionCase, EvidenceValue, ResolvedContext, ResolvedValue, utc


def resolve_case_context(
    case: DecisionCase,
    evidence: Iterable[EvidenceValue],
    *,
    required_fields: Iterable[str] = (),
) -> ResolvedContext:
    """Reject future knowledge; preserve stale/missing values instead of filling them."""
    values: dict[str, list[ResolvedValue]] = {}
    seen: set[tuple[str, datetime | None]] = set()
    for item in evidence:
        key = (item.field, utc(item.valid_at) if item.valid_at else None)
        if key in seen:
            raise ValueError(f"duplicate evidence for {item.field} at {item.valid_at}")
        seen.add(key)
        if item.value is not None and any(
            utc(when) > utc(case.as_of)
            for when in (item.available_at, item.observed_at, item.issued_at)
            if when is not None
        ):
            raise ValueError(f"{item.field} was unavailable at the decision time")
        if item.value is None:
            resolved = ResolvedValue(evidence=item, status="missing", reason="No supplied value")
        else:
            reference = item.observed_at if item.source_type == "measurement" else item.available_at
            assert reference is not None
            age = (utc(case.as_of) - utc(reference)).total_seconds()
            if item.max_age_seconds is not None and age > item.max_age_seconds:
                resolved = ResolvedValue(evidence=item, status="stale", reason="Source age exceeds its freshness limit")
            else:
                resolved = ResolvedValue(evidence=item, status="available")
        values.setdefault(item.field, []).append(resolved)
    for field in values:
        values[field].sort(key=lambda item: utc(item.evidence.valid_at) if item.evidence.valid_at else utc(case.as_of))
    missing = sorted(field for field in set(required_fields) if not any(
        item.status == "available" for item in values.get(field, [])
    ))
    return ResolvedContext(case=case, values=values, missing_fields=missing)


def evidence_from_gfs_snapshot(snapshot: dict, *, as_of: datetime) -> list[EvidenceValue]:
    """Adapt the checked *national constraint* snapshot without changing its claims."""
    rows = validate_snapshot(snapshot, as_of=as_of)
    return [
        EvidenceValue(
            field="constraint_mwh",
            value=row["expected_constraint_mwh"],
            unit="MWh per half-hour",
            source_type="forecast",
            source="NOAA GFS national constraint experimental model",
            source_version=snapshot["model"]["artifact_sha256"],
            available_at=snapshot["generated_at_utc"],
            issued_at=snapshot["issue_time_utc"],
            valid_at=row["target_time_utc"],
            max_age_seconds=24 * 3600,
            lower_bound=row["lower_90_mwh"],
            upper_bound=row["upper_90_mwh"],
            limitation="National constraint only; experimental, not a locational or curtailment forecast.",
        )
        for row in rows
    ]
