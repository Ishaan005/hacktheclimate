"""Conservative safety screening for planning-case network scenarios.

PASS here means only that a check's stated model and evidence passed. An
overall PASS requires every required check to pass; this prototype cannot
establish voltage, inertia or RoCoF from a DC power-flow result.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping

Status = Literal["PASS", "FAIL", "UNKNOWN"]


@dataclass(frozen=True)
class CheckResult:
    status: Status
    reason: str
    evidence: str | None = None


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
    if any(check.status == "FAIL" for check in checks.values()):
        return "FAIL"
    if any(check.status == "UNKNOWN" for check in checks.values()):
        return "UNKNOWN"
    return "PASS"


def evaluate_safety(
    solve: Mapping[str, Any],
    *,
    snsp_pct: float | None = None,
    snsp_limit_pct: float = 75.0,
    externally_verified: Mapping[str, CheckResult] | None = None,
) -> SafetyResult:
    """Evaluate required checks without turning missing evidence into PASS.

    ``externally_verified`` is for a future reviewed AC/system-security source.
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
