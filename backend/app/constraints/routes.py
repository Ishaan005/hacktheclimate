from fastapi import APIRouter, HTTPException
from .checker import get_constraint_checker

router = APIRouter(prefix="/v1/constraints", tags=["constraint checker"])


@router.get("/check")
def check_constraint(timestamp: str, horizon_hours: int = 1):
    if horizon_hours not in {1, 4, 6, 12, 24}:
        raise HTTPException(422, "Supported horizons are 1, 4, 6, 12, and 24 hours.")

    try:
        return get_constraint_checker().check(timestamp, horizon_hours)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc