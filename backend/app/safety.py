"""Conservative safety screening for planning-case network scenarios.

PASS here means only that a check's stated model and evidence passed. An
overall PASS requires every required check to pass; this prototype cannot
establish voltage, inertia or RoCoF from a DC power-flow result.

The family-level helpers expose operator-facing safety evidence without
pretending that the planning model is a live security study. Missing evidence
remains UNKNOWN and NOT_APPLICABLE checks are excluded from family roll-ups.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping

Status = Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]


@dataclass(frozen=True)
class CheckResult:
    status: Status
    reason: str
    evidence: str | None = None
    value: float | None = None
    unit: str | None = None
    asset_id: str | None = None


@dataclass(frozen=True)
class SafetyFamilyResult:
    family_id: str
    overall: Status
    checks: dict[str, CheckResult]

    @property
    def recommendable(self) -> bool:
        return self.overall == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "overall": self.overall,
            "checks": {name: asdict(check) for name, check in self.checks.items()},
            "recommendable": self.recommendable,
        }


@dataclass(frozen=True)
class SafetyResult:
    overall: Status
    thermal: CheckResult
    islanding: CheckResult
    snsp: CheckResult
    voltage: CheckResult
    inertia: CheckResult
    rocof: CheckResult

    @property
    def recommendable(self) -> bool:
        return self.overall == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "recommendable": self.recommendable}


def combine_checks(checks: Mapping[str, CheckResult]) -> Status:
    applicable = [
        check for check in checks.values()
        if check.status != "NOT_APPLICABLE"
    ]
    if any(check.status == "FAIL" for check in applicable):
        return "FAIL"
    if any(check.status == "UNKNOWN" for check in applicable) or not applicable:
        return "UNKNOWN"
    return "PASS"


def _rated_flow_margins(solve: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return rating minus absolute DC flow for assets with usable ratings."""
    if solve.get("status") != "ok":
        return []
    margins = []
    for flow in solve.get("flows", []):
        rating = flow.get("rating_mva")
        if rating is None:
            continue
        rating = float(rating)
        flow_mw = float(flow["flow_mw"])
        if not math.isfinite(rating) or not math.isfinite(flow_mw) or rating <= 0:
            continue
        margins.append({
            "asset_type": str(flow.get("asset_type", "")),
            "asset_id": str(flow.get("asset_id", "")),
            "margin_mva_proxy": rating - abs(flow_mw),
            "rating_mva": rating,
            "flow_mw": flow_mw,
        })
    return margins


def _thermal_margin_check(
    solve: Mapping[str, Any],
    *,
    label: str,
) -> CheckResult:
    if solve.get("status") != "ok":
        return CheckResult(
            "UNKNOWN",
            f"{label} network solve is not a connected solved state.",
            "DC planning power-flow screen",
        )
    flows = list(solve.get("flows", []))
    margins = _rated_flow_margins(solve)
    if not flows:
        return CheckResult(
            "UNKNOWN",
            f"{label} solve contains no branch or transformer flows.",
            "DC planning power-flow screen",
        )
    if len(margins) != len(flows):
        return CheckResult(
            "UNKNOWN",
            f"{label} has one or more assets without a usable planning rating.",
            "TYTFS rate A DC proxy",
        )
    limiting = min(margins, key=lambda item: item["margin_mva_proxy"])
    margin = float(limiting["margin_mva_proxy"])
    return CheckResult(
        "PASS" if margin >= -1e-9 else "FAIL",
        (
            f"{label} minimum modeled thermal margin is "
            f"{margin:.2f} MVA-proxy on {limiting['asset_id']}."
        ),
        "TYTFS rate A DC proxy",
        value=margin,
        unit="MVA-proxy",
        asset_id=limiting["asset_id"],
    )


def _new_bottleneck_check(
    base_solve: Mapping[str, Any],
    action_solve: Mapping[str, Any],
) -> CheckResult:
    if base_solve.get("status") != "ok" or action_solve.get("status") != "ok":
        return CheckResult(
            "UNKNOWN",
            "Base and candidate states must both solve before checking for a shifted bottleneck.",
            "DC planning power-flow comparison",
        )
    before = {
        (item["asset_type"], item["asset_id"]): item
        for item in _rated_flow_margins(base_solve)
    }
    after = {
        (item["asset_type"], item["asset_id"]): item
        for item in _rated_flow_margins(action_solve)
    }
    comparable = sorted(set(before).intersection(after))
    if not comparable:
        return CheckResult(
            "UNKNOWN",
            "No commonly rated assets are available for the bottleneck comparison.",
            "DC planning power-flow comparison",
        )

    created = []
    for key in comparable:
        old_margin = float(before[key]["margin_mva_proxy"])
        new_margin = float(after[key]["margin_mva_proxy"])
        if old_margin >= -1e-9 and new_margin < -1e-9:
            created.append((key, old_margin, new_margin))

    if created:
        key, _, new_margin = min(created, key=lambda item: item[2])
        return CheckResult(
            "FAIL",
            (
                "The candidate creates a new modeled overload on "
                f"{key[1]} with margin {new_margin:.2f} MVA-proxy."
            ),
            "DC planning power-flow comparison",
            value=new_margin,
            unit="MVA-proxy",
            asset_id=key[1],
        )

    limiting_key = min(
        comparable,
        key=lambda key: float(after[key]["margin_mva_proxy"]),
    )
    limiting_margin = float(after[limiting_key]["margin_mva_proxy"])
    return CheckResult(
        "PASS",
        "The candidate does not create a new rated-asset overload in the modeled state.",
        "DC planning power-flow comparison",
        value=limiting_margin,
        unit="MVA-proxy",
        asset_id=limiting_key[1],
    )


def evaluate_transmission_family(
    base_solve: Mapping[str, Any],
    action_solve: Mapping[str, Any],
    *,
    base_contingency_solve: Mapping[str, Any] | None = None,
    action_contingency_solve: Mapping[str, Any] | None = None,
    relief_timing_verified: bool | None = None,
) -> SafetyFamilyResult:
    """Evaluate the transmission-family gates for a full candidate state.

    The margins are planning DC/MVA proxies, not live operational ratings. A
    credible-failure result is UNKNOWN unless a contingency solve is supplied.
    Timing is UNKNOWN unless upstream evidence explicitly verifies that relief
    arrives before the modeled breach.
    """
    current_margin = _thermal_margin_check(
        action_solve,
        label="Candidate",
    )
    if action_contingency_solve is None:
        contingency_margin = CheckResult(
            "UNKNOWN",
            "No credible-failure solve was supplied for this candidate state.",
            "DC contingency screen",
        )
    else:
        contingency_margin = _thermal_margin_check(
            action_contingency_solve,
            label="Credible-failure candidate",
        )

    planned_bottleneck = _new_bottleneck_check(base_solve, action_solve)
    bottleneck_checks = {"planned_state": planned_bottleneck}
    if base_contingency_solve is not None or action_contingency_solve is not None:
        contingency_bottleneck = (
            _new_bottleneck_check(
                base_contingency_solve,
                action_contingency_solve,
            )
            if (
                base_contingency_solve is not None
                and action_contingency_solve is not None
            )
            else CheckResult(
                "UNKNOWN",
                "Both base and candidate credible-failure solves are required "
                "to check for a shifted contingency bottleneck.",
                "DC contingency comparison",
            )
        )
        bottleneck_checks["credible_failure_state"] = contingency_bottleneck

    bottleneck_status = combine_checks(bottleneck_checks)
    if bottleneck_status == "FAIL":
        source_check = next(
            check for check in bottleneck_checks.values() if check.status == "FAIL"
        )
    elif bottleneck_status == "UNKNOWN":
        source_check = next(
            check for check in bottleneck_checks.values() if check.status == "UNKNOWN"
        )
    else:
        source_check = min(
            bottleneck_checks.values(),
            key=lambda check: check.value if check.value is not None else math.inf,
        )
    new_bottleneck = CheckResult(
        bottleneck_status,
        source_check.reason,
        source_check.evidence,
        value=source_check.value,
        unit=source_check.unit,
        asset_id=source_check.asset_id,
    )

    if relief_timing_verified is True:
        time_to_relief = CheckResult(
            "PASS",
            "Action timing evidence verifies relief is available before the modeled breach.",
            "action timing evidence",
        )
    elif relief_timing_verified is False:
        time_to_relief = CheckResult(
            "FAIL",
            "Action timing evidence shows relief arrives after the modeled breach.",
            "action timing evidence",
        )
    else:
        time_to_relief = CheckResult(
            "UNKNOWN",
            "Response-time and breach-time evidence are not yet wired into the planning screen.",
        )

    checks = {
        "current_forecast_thermal_margin": current_margin,
        "worst_credible_failure_margin": contingency_margin,
        "new_bottleneck": new_bottleneck,
        "time_to_relief": time_to_relief,
    }
    return SafetyFamilyResult(
        family_id="transmission",
        overall=combine_checks(checks),
        checks=checks,
    )



def _unavailable_family_check(label: str) -> CheckResult:
    return CheckResult(
        "UNKNOWN",
        f"No reviewed {label} calculation, limit, and current evidence are available.",
    )


def evaluate_high_frequency_min_generation_family(
    *,
    frequency_margin: CheckResult | None = None,
    minimum_conventional_units: CheckResult | None = None,
    reserve_margin: CheckResult | None = None,
    ramping_margin: CheckResult | None = None,
) -> SafetyFamilyResult:
    """Evaluate the high-frequency/minimum-generation family conservatively.

    Callers may supply reviewed CheckResult values from an authoritative
    calculation or source. Missing gates stay UNKNOWN rather than inheriting
    assumptions from the DC network model.
    """
    checks = {
        "frequency_margin": frequency_margin or _unavailable_family_check(
            "frequency-margin"
        ),
        "minimum_conventional_units": (
            minimum_conventional_units
            or _unavailable_family_check("minimum-conventional-unit")
        ),
        "reserve_margin": reserve_margin or _unavailable_family_check(
            "reserve-margin"
        ),
        "ramping_margin": ramping_margin or _unavailable_family_check(
            "ramping-margin"
        ),
    }
    return SafetyFamilyResult(
        family_id="high_frequency_minimum_generation",
        overall=combine_checks(checks),
        checks=checks,
    )


def evaluate_snsp_family(
    *,
    snsp_pct: float | None = None,
    approved_snsp_limit_pct: float | None = None,
    inertia_frequency_stability: CheckResult | None = None,
    duration_concurrent_limits: CheckResult | None = None,
) -> SafetyFamilyResult:
    """Evaluate SNSP ratio plus dynamic/duration evidence without inventing limits."""
    if snsp_pct is None:
        ratio = CheckResult(
            "UNKNOWN",
            "No point-in-time SNSP value was supplied.",
        )
    else:
        value = float(snsp_pct)
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("snsp_pct must be within [0, 100]")
        if approved_snsp_limit_pct is None:
            ratio = CheckResult(
                "UNKNOWN",
                "SNSP value is available but no approved scenario limit is wired.",
                "supplied point-in-time SNSP",
                value=value,
                unit="percent",
            )
        else:
            limit = float(approved_snsp_limit_pct)
            if not math.isfinite(limit) or not 0 < limit <= 100:
                raise ValueError("approved_snsp_limit_pct must be within (0, 100]")
            margin = limit - value
            ratio = CheckResult(
                "PASS" if margin >= -1e-9 else "FAIL",
                (
                    f"SNSP margin to approved limit is {margin:.2f} percentage points "
                    f"({value:.2f}% versus {limit:.2f}%)."
                ),
                "supplied point-in-time SNSP and approved policy limit",
                value=margin,
                unit="percentage_points",
            )

    checks = {
        "snsp_ratio_margin": ratio,
        "inertia_frequency_stability": (
            inertia_frequency_stability
            or _unavailable_family_check("inertia/frequency-stability")
        ),
        "duration_concurrent_limits": (
            duration_concurrent_limits
            or _unavailable_family_check("SNSP-duration/concurrent-limit")
        ),
    }
    return SafetyFamilyResult(
        family_id="snsp",
        overall=combine_checks(checks),
        checks=checks,
    )


def evaluate_safety(
    solve: Mapping[str, Any],
    *,
    snsp_pct: float | None = None,
    snsp_limit_pct: float = 75.0,
    externally_verified: Mapping[str, CheckResult] | None = None,
) -> SafetyResult:
    """Evaluate required checks without turning missing evidence into PASS.

    externally_verified is for a future reviewed AC/system-security source.
    The current network forecast and operator API never supply it.
    """
    if not math.isfinite(snsp_limit_pct) or not 0 < snsp_limit_pct <= 100:
        raise ValueError("snsp_limit_pct must be within (0, 100]")
    if solve.get("status") == "islanded":
        islanding = CheckResult("FAIL", "The AC scenario has disconnected components.", "DC topology screen")
    elif solve.get("status") == "ok":
        islanding = CheckResult("PASS", "No new modeled AC island is present.", "DC topology screen")
    else:
        islanding = CheckResult("UNKNOWN", "The network solve did not complete.", "DC topology screen")

    flows = solve.get("flows", []) if solve.get("status") == "ok" else []
    rated = [flow for flow in flows if flow.get("loading_pct") is not None]
    if not flows:
        thermal = CheckResult("UNKNOWN", "No solved branch flows are available.")
    elif any(float(flow["loading_pct"]) > 100 for flow in rated):
        thermal = CheckResult("FAIL", "At least one modeled MW/MVA rating proxy exceeds 100%.", "TYTFS rate A DC proxy")
    elif len(rated) != len(flows):
        thermal = CheckResult("UNKNOWN", "Some modeled assets lack a usable rate A; thermal safety is incomplete.", "TYTFS rate A DC proxy")
    else:
        thermal = CheckResult("PASS", "All modeled MW/MVA rating proxies are at or below 100%.", "TYTFS rate A DC proxy")

    if snsp_pct is None:
        snsp = CheckResult("UNKNOWN", "No point-in-time SNSP forecast was supplied.")
    else:
        value = float(snsp_pct)
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("snsp_pct must be within [0, 100]")
        snsp = CheckResult(
            "PASS" if value <= snsp_limit_pct else "FAIL",
            f"Supplied SNSP {value:.2f}% versus scenario rule {snsp_limit_pct:.2f}%.",
            "supplied point-in-time SNSP forecast",
            value=value,
            unit="percent",
        )

    unknown = {
        name: CheckResult("UNKNOWN", f"{name.capitalize()} cannot be evaluated from this DC planning case.")
        for name in ("voltage", "inertia", "rocof")
    }
    verified = dict(externally_verified or {})
    if set(verified) - set(unknown):
        raise ValueError("externally_verified contains an unsupported check")
    if any(not isinstance(value, CheckResult) or not value.evidence for value in verified.values()):
        raise ValueError("external checks need a CheckResult with evidence")
    unknown.update(verified)
    checks = {"thermal": thermal, "islanding": islanding, "snsp": snsp, **unknown}
    return SafetyResult(overall=combine_checks(checks), **checks)
