from fastapi import APIRouter, HTTPException

from .predictor import get_dispatch_down_predictor

router = APIRouter(prefix="/v1/dispatch-down", tags=["dispatch-down forecast"])


@router.get("/forecast")
def forecast_dispatch_down(target_timestamp: str):
    """Return a one-hour-ahead historical dispatch-down risk prediction."""
    try:
        return get_dispatch_down_predictor().predict(target_timestamp)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
