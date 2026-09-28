from fastapi import APIRouter, HTTPException

from .checker import SUPPORTED_HORIZONS, get_constraint_checker

router = APIRouter(prefix="/v1/constraints", tags=["constraint checker"])


@router.get("/check")
def check_constraint(timestamp: str, horizon_hours: int = 1):
    """Historical replay of the national constraint forecast for one target half-hour."""
    if horizon_hours not in SUPPORTED_HORIZONS:
        raise HTTPException(422, f"Supported horizons are {', '.join(map(str, SUPPORTED_HORIZONS))} hours.")
    try:
        checker = get_constraint_checker()
    except FileNotFoundError as exc:
        raise HTTPException(503, f"Constraint model inputs are missing: {exc}") from exc
    try:
        return checker.check(timestamp, horizon_hours)
    except FileNotFoundError as exc:
        raise HTTPException(503, f"Constraint model artifact is missing: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
