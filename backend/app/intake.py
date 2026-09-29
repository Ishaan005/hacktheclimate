"""POST /v1/intake: turn the operator's description into a case to review.

Only facts the operator actually stated are extracted. Forecast, measured and
asset-register facts are never taken from free text, so the workspace still
asks for (or fetches) them. Anything not stated stays out of the case, which
the frontend treats as unknown.

Extraction uses Azure OpenAI when chat is configured and falls back to
keyword rules otherwise, or when the model call fails.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/intake", tags=["operator intake"])

ScenarioFamily = Literal["local_network_constraint", "system_wide_curtailment", "planned_outage_exposure", "cause_unknown"]
ActionFamily = Literal["storage_charging", "flexible_demand", "generator_redispatch", "outage_review"]

# Facts an operator may state in words (their `sources` in frontend/src/case.ts
# include 'operator'). key -> unit.
SITUATION_FACTS: dict[str, str | None] = {
    "event_window": None,
    "affected_area": None,
    "existing_instructions": None,
}
ACTION_FACTS: dict[str, dict[str, str | None]] = {
    "storage_charging": {"connection_location": None, "max_charging_mw": "MW", "available_mwh": "MWh",
                         "state_of_charge_pct": "%", "earliest_start": None, "activation_delay_min": "min"},
    "flexible_demand": {"connection_location": None, "available_mw": "MW", "direction": None, "available_mwh": "MWh",
                        "demand_baseline_mw": "MW", "rebound_mwh": "MWh", "earliest_start": None,
                        "activation_delay_min": "min", "max_duration_min": "min"},
    "generator_redispatch": {"connection_location": None, "scheduled_output_mw": "MW", "min_stable_generation_mw": "MW",
                             "max_output_mw": "MW", "ramp_rate_mw_per_min": "MW/min", "commitment_restrictions": None},
    "outage_review": {"outage_id": None, "alternative_window": None},
}
SCENARIOS = {"local_network_constraint", "system_wide_curtailment", "planned_outage_exposure"}


class IntakeRequest(BaseModel):
    description: str = Field(min_length=1, max_length=4000)
    comparison_text: str | None = Field(default=None, max_length=4000)
    created_at: datetime


class IntakeResponse(BaseModel):
    case: dict[str, Any]
    extraction: Literal["llm", "rules"]


# ---------- rules ----------

ACTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("outage_review", re.compile(r"\b(reschedul\w*|move the outage|outage review|review the outage)\b", re.I)),
    ("storage_charging", re.compile(r"\b(battery|storage|pumped)\b", re.I)),
    ("flexible_demand", re.compile(r"\b(flexible demand|demand response|data cent(re|er)|workload|ev charging)\b", re.I)),
    ("generator_redispatch", re.compile(r"\b(generator|redispatch|unit output)\b", re.I)),
]
SCENARIO_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("system_wide_curtailment", re.compile(r"\b(snsp|inertia|minimum units?|system[- ]wide|curtail\w*)\b", re.I)),
    ("local_network_constraint", re.compile(r"\b(line|transformer|circuit|thermal|overload\w*|constraint group|local constraint|congest\w*)\b", re.I)),
    ("planned_outage_exposure", re.compile(r"\b(planned outage|outage|maintenance)\b", re.I)),
]
WINDOW = re.compile(r"\b(\d{1,2}:\d{2})\s*(?:-|–|—|to|until)\s*(\d{1,2}:\d{2})\b", re.I)
RELATIVE_WINDOW = re.compile(r"\b(?:for\s+)?the\s+next\s+(\d+(?:\.\d+)?)\s*(hours?|hrs?)\b", re.I)
AREA_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("North-west", re.compile(r"\bnorth[- ]?west\b", re.I)),
    ("South-west", re.compile(r"\bsouth[- ]?west\b", re.I)),
    ("South-east", re.compile(r"\bsouth[- ]?east\b", re.I)),
    ("North-east", re.compile(r"\bnorth[- ]?east\b", re.I)),
    ("Midlands", re.compile(r"\bmidlands?\b", re.I)),
    ("Dublin", re.compile(r"\bdublin\b", re.I)),
    ("West", re.compile(r"\bwest(?:ern)?\b", re.I)),
    ("South", re.compile(r"\bsouth(?:ern)?\b", re.I)),
    ("North", re.compile(r"\bnorth(?:ern)?\b", re.I)),
    ("All-island", re.compile(r"\b(all[- ]island|system[- ]wide)\b", re.I)),
]
ASSET = re.compile(r"\b(Battery|Storage|Generator|Unit|Load|Flexible load) [A-Z0-9]+\b")
NUMBER_FACTS: dict[str, list[tuple[str, re.Pattern]]] = {
    "storage_charging": [
        ("max_charging_mw", re.compile(r"(\d+(?:\.\d+)?)\s*MW\b(?!h)", re.I)),
        ("available_mwh", re.compile(r"(\d+(?:\.\d+)?)\s*MWh\b", re.I)),
        ("state_of_charge_pct", re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:state of charge|soc|charged|full)", re.I)),
    ],
    "flexible_demand": [
        ("available_mw", re.compile(r"(\d+(?:\.\d+)?)\s*MW\b(?!h)", re.I)),
        ("available_mwh", re.compile(r"(\d+(?:\.\d+)?)\s*MWh\b", re.I)),
    ],
    "generator_redispatch": [("scheduled_output_mw", re.compile(r"(\d+(?:\.\d+)?)\s*MW\b(?!h)", re.I))],
    "outage_review": [("outage_id", re.compile(r"\boutage\s+(?:id\s*)?([A-Z]{1,4}[-_ ]?\d{2,})\b", re.I))],
}


def _rules_situation(text: str) -> dict[str, Any]:
    scenarios = [family for family, pattern in SCENARIO_PATTERNS if pattern.search(text)]
    facts: dict[str, Any] = {}
    if match := WINDOW.search(text):
        facts["event_window"] = f"{match.group(1)}–{match.group(2)}"
    elif match := RELATIVE_WINDOW.search(text):
        amount = float(match.group(1))
        label = int(amount) if amount.is_integer() else amount
        facts["event_window"] = f"next {label} hours"
    for label, pattern in AREA_PATTERNS:
        if pattern.search(text):
            facts["affected_area"] = label
            break
    return {"scenarios": scenarios, "facts": facts}


def _rules_action(text: str) -> dict[str, Any] | None:
    family = next((f for f, pattern in ACTION_PATTERNS if pattern.search(text)), None)
    if family is None:
        return None
    facts: dict[str, Any] = {}
    for key, pattern in NUMBER_FACTS.get(family, []):
        if match := pattern.search(text):
            raw = match.group(1)
            facts[key] = raw if key == "outage_id" else float(raw)
    if family == "flexible_demand":
        if re.search(r"\b(increase|raise|turn up|absorb)\b", text, re.I):
            facts["direction"] = "increase"
        elif re.search(r"\b(decrease|reduce|cut|turn down|shed)\b", text, re.I):
            facts["direction"] = "decrease"
    asset = ASSET.search(text)
    return {"family": family, "asset_name": asset.group(0) if asset else None, "facts": facts}


def extract_with_rules(text: str) -> dict[str, Any]:
    return {**_rules_situation(text), "action": _rules_action(text)}


# ---------- LLM ----------

LLM_PROMPT = """Extract a grid-operator case from the operator's text. Return JSON only:
{"scenarios": [...], "facts": {...}, "action": null | {"family": ..., "asset_name": str|null, "facts": {...}}}

scenarios: any of local_network_constraint (a line, transformer or area limit), system_wide_curtailment
(SNSP, inertia, minimum units), planned_outage_exposure (a planned outage worsens the limit). Empty if not stated.
facts (situation): only these keys: %s
action.family: one of storage_charging, flexible_demand, generator_redispatch, outage_review, or action null.
action.facts: only keys allowed for that family: %s

Rules: include a key ONLY if the operator explicitly stated its value. Never estimate, infer or fill defaults.
Numbers as plain numbers in the listed unit. Omit everything else."""


def extract_with_llm(text: str) -> dict[str, Any]:
    from langchain_core.messages import HumanMessage, SystemMessage

    from .chat.config import get_settings
    from .chat.graph import build_azure_llm

    settings = get_settings()
    if not settings.configured:
        raise RuntimeError("chat not configured")
    prompt = LLM_PROMPT % (
        ", ".join(SITUATION_FACTS),
        json.dumps({family: list(keys) for family, keys in ACTION_FACTS.items()}),
    )
    llm = build_azure_llm(settings)
    reply = llm.invoke([SystemMessage(prompt), HumanMessage(text)])
    raw = str(reply.content).strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    return json.loads(raw)


# ---------- build the case ----------

def _fact(key: str, value: Any, unit: str | None, source_name: str, as_of: str) -> dict[str, Any]:
    return {"key": key, "value": value, "unit": unit, "status": "supplied", "source": "operator",
            "sourceName": source_name, "asOf": as_of, "history": []}


def _clean_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    return text[:200] or None


def _facts(raw: Any, allowed: dict[str, str | None], source_name: str, as_of: str) -> dict[str, Any]:
    """Keep only allowed keys with a real value; everything else stays unknown."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    for key, value in raw.items():
        if key not in allowed:
            continue
        value = _clean_value(value)
        if value is None:
            continue
        if key == "direction" and value not in ("increase", "decrease"):
            continue
        out[key] = _fact(key, value, allowed[key], source_name, as_of)
    return out


def _action(raw: Any, source_name: str, as_of: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or raw.get("family") not in ACTION_FACTS:
        return None
    family = raw["family"]
    asset = raw.get("asset_name")
    return {"family": family, "assetName": str(asset)[:120] if asset else None,
            "facts": _facts(raw.get("facts"), ACTION_FACTS[family], source_name, as_of)}


def build_case(text: str, extracted: dict[str, Any], created_at: str, source_name: str) -> dict[str, Any]:
    scenarios = [s for s in extracted.get("scenarios") or [] if s in SCENARIOS]
    return {
        "id": f"case-{created_at}",
        "originalText": text,
        "createdAt": created_at,
        "scenarios": list(dict.fromkeys(scenarios)) or ["cause_unknown"],
        "facts": _facts(extracted.get("facts"), SITUATION_FACTS, source_name, created_at),
        "proposedAction": _action(extracted.get("action"), source_name, created_at),
        "comparison": None,
    }


def _extract(text: str) -> tuple[dict[str, Any], Literal["llm", "rules"]]:
    try:
        return extract_with_llm(text), "llm"
    except Exception as exc:  # no Azure config, network error or bad JSON: rules still work
        logger.info("Intake LLM extraction unavailable (%s); using rules", type(exc).__name__)
        return extract_with_rules(text), "rules"


SOURCE_NAMES = {"llm": "Operator description (LLM extraction)", "rules": "Operator description (keyword rules)"}


@router.post("", response_model=IntakeResponse)
def intake(request: IntakeRequest) -> IntakeResponse:
    created_at = request.created_at.isoformat().replace("+00:00", "Z")
    extracted, method = _extract(request.description)
    case = build_case(request.description, extracted, created_at, SOURCE_NAMES[method])
    comparison_text = (request.comparison_text or "").strip()
    if comparison_text:
        # Reuse the same method so the whole case is labelled consistently.
        try:
            other = extract_with_llm(comparison_text) if method == "llm" else extract_with_rules(comparison_text)
        except Exception:
            other = extract_with_rules(comparison_text)
        action = _action(other.get("action"), SOURCE_NAMES[method], created_at)
        if action:
            case["comparison"] = {"kind": "action", "originalText": comparison_text, "action": action}
        else:
            case["comparison"] = {"kind": "situation", "originalText": comparison_text,
                                  "situation": build_case(comparison_text, other, created_at, SOURCE_NAMES[method])}
    return IntakeResponse(case=case, extraction=method)
