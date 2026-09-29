"""Contracts shared with intake, action calculation, and the decision screen."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


def utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return value.astimezone(timezone.utc)


class ExistingInstruction(Contract):
    instruction_id: str
    starts_at: datetime
    ends_at: datetime
    evidence_reference: str
    included_in_forecast: bool
    constraint_delta_mwh_per_interval: float | None = None
    curtailment_delta_mwh_per_interval: float | None = None

    @model_validator(mode="after")
    def valid_effect(self):
        if utc(self.starts_at) >= utc(self.ends_at):
            raise ValueError("instruction window must be positive")
        if not self.evidence_reference.strip():
            raise ValueError("instruction needs an evidence reference")
        if not self.included_in_forecast and self.constraint_delta_mwh_per_interval is None and self.curtailment_delta_mwh_per_interval is None:
            raise ValueError("an unreflected instruction needs a quantified effect")
        if any(not isfinite(value) for value in (self.constraint_delta_mwh_per_interval, self.curtailment_delta_mwh_per_interval) if value is not None):
            raise ValueError("instruction effects must be finite")
        return self


class DecisionCase(Contract):
    schema_version: Literal[1] = 1
    case_id: str
    scenario_ids: list[str] = Field(min_length=1)
    location: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    as_of: datetime
    starts_at: datetime
    ends_at: datetime
    existing_instructions: list[ExistingInstruction] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_window(self):
        start, end, decision = utc(self.starts_at), utc(self.ends_at), utc(self.as_of)
        if end - start != timedelta(hours=24):
            raise ValueError("decision window must contain exactly 24 hours")
        if start <= decision or start.minute not in (0, 30) or start.second or start.microsecond:
            raise ValueError("decision window must start on a future UTC half-hour")
        if not self.case_id.strip() or any(not item.strip() for item in self.scenario_ids):
            raise ValueError("case and scenario IDs must be nonempty")
        if len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ValueError("scenario IDs must be unique")
        return self


class EvidenceValue(Contract):
    field: str
    value: float | str | bool | None
    unit: str
    source_type: Literal["operator", "measurement", "forecast", "planning_model"]
    source: str
    source_version: str
    available_at: datetime | None = None
    observed_at: datetime | None = None
    issued_at: datetime | None = None
    valid_at: datetime | None = None
    max_age_seconds: int | None = Field(default=None, ge=0)
    lower_bound: float | None = Field(default=None, ge=0)
    upper_bound: float | None = Field(default=None, ge=0)
    limitation: str | None = None

    @model_validator(mode="after")
    def valid_provenance(self):
        for value in (self.available_at, self.observed_at, self.issued_at, self.valid_at):
            if value is not None:
                utc(value)
        if self.value is not None and (self.available_at is None or not self.source.strip() or not self.source_version.strip()):
            raise ValueError("supplied evidence needs availability and source version")
        if self.value is not None and self.max_age_seconds is None:
            raise ValueError("supplied evidence needs an explicit freshness limit")
        if self.source_type == "forecast" and self.value is not None and (self.issued_at is None or self.valid_at is None):
            raise ValueError("forecast evidence needs issue and valid times")
        if self.source_type == "measurement" and self.value is not None and self.observed_at is None:
            raise ValueError("measurement evidence needs an observation time")
        if self.available_at is not None and any(
            utc(source_time) > utc(self.available_at)
            for source_time in (self.observed_at, self.issued_at) if source_time is not None
        ):
            raise ValueError("source time cannot be later than availability time")
        if isinstance(self.value, float) and not isfinite(self.value):
            raise ValueError("evidence value must be finite")
        if self.lower_bound is not None and (not isfinite(self.lower_bound) or isinstance(self.value, (int, float)) and self.lower_bound > self.value):
            raise ValueError("lower bound must be finite and no higher than the value")
        if self.upper_bound is not None and (not isfinite(self.upper_bound) or isinstance(self.value, (int, float)) and self.upper_bound < self.value):
            raise ValueError("upper bound must be finite and no lower than the value")
        return self


class ResolvedValue(Contract):
    evidence: EvidenceValue
    status: Literal["available", "stale", "missing"]
    reason: str | None = None


class ResolvedContext(Contract):
    case: DecisionCase
    values: dict[str, list[ResolvedValue]]
    missing_fields: list[str]


class SourceReference(Contract):
    reference: str
    kind: Literal["measured", "estimated", "modelled"]

    @model_validator(mode="after")
    def nonempty_reference(self):
        if not self.reference.strip():
            raise ValueError("source reference must be nonempty")
        return self


class PastCase(Contract):
    schema_version: Literal[1] = 1
    record_id: str
    scenario_ids: list[str] = Field(min_length=1)
    location: str | None = None
    conditions: dict[str, float | str] = Field(default_factory=dict)
    action_id: str
    starts_at: datetime
    ends_at: datetime
    available_at: datetime
    baseline_metrics_mwh: dict[str, float | None]
    outcome_metrics_mwh: dict[str, float | None]
    outcome_label: Literal["observed", "estimated", "modelled"]
    quality: Literal["high", "medium", "low"]
    sources: list[SourceReference] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_record(self):
        if utc(self.starts_at) >= utc(self.ends_at) or utc(self.available_at) < utc(self.ends_at):
            raise ValueError("case record times are inconsistent")
        if not self.record_id.strip() or not self.action_id.strip() or any(not item.strip() for item in self.scenario_ids):
            raise ValueError("case record IDs must be nonempty")
        if self.outcome_label == "observed" and not any(source.kind == "measured" for source in self.sources):
            raise ValueError("observed outcomes need measured case-level evidence")
        if any(value is not None and (not isfinite(value) or value < 0) for metrics in (self.baseline_metrics_mwh, self.outcome_metrics_mwh) for value in metrics.values()):
            raise ValueError("case energy metrics must be finite and nonnegative")
        return self
