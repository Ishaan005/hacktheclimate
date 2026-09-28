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


@router.get("/forecast/day")
def forecast_dispatch_down_day(target_timestamp: str):
    """Return the half-hourly replay predictions for the UTC day of a target time."""
    try:
        return get_dispatch_down_predictor().predict_day(target_timestamp)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
