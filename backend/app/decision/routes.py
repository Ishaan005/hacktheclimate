"""Read-only case preview while scenario and action contracts await review."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import Field

from .cases import load_cases
from .contracts import Contract, DecisionCase, utc
from .manifest import load_contract_manifest
from .policy import load_demo_policy
from .scenarios import ScenarioCatalogue, load_scenario_catalogue
from .service import CaseEvaluation, evaluate_case
from .sources import load_checked_constraint

router = APIRouter(prefix="/v1/decision", tags=["advisory decision preview"])


class PreviewRequest(Contract):
    case: DecisionCase
    conditions: dict[str, float | str] = Field(default_factory=dict)
    include_modelled_demo_cases: bool = False


@router.get("/scenarios", response_model=ScenarioCatalogue)
def scenario_catalogue() -> ScenarioCatalogue:
    """The locked identification catalogue; actions and safety inputs remain separate."""
    return load_scenario_catalogue()


@router.post("/preview", response_model=CaseEvaluation)
def preview_case(request: PreviewRequest) -> CaseEvaluation:
    """No client-supplied forecast or safety check can enter this endpoint."""
    if utc(request.case.as_of) > datetime.now(timezone.utc) + timedelta(minutes=1):
        raise HTTPException(422, "case decision time cannot be in the future")
    source = load_checked_constraint(request.case.as_of)
    if source.status == "available":
        source = source.model_copy(update={
            "status": "inapplicable",
            "reason": "Experimental national constraint total cannot establish an issue #47 scenario baseline",
            "values": [],
        })
    return evaluate_case(
        request.case, evidence=source.values, sources=[source],
        manifest=load_contract_manifest(), policy=load_demo_policy(),
        past_cases=load_cases() if request.include_modelled_demo_cases else [],
        conditions=request.conditions,
    )
