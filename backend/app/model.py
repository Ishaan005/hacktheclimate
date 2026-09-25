from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import average_precision_score, mean_absolute_error


@dataclass
class DispatchDownModels:
    occurrence: HistGradientBoostingClassifier
    volume: HistGradientBoostingRegressor


def train_hurdle_model(X: pd.DataFrame, dispatch_down_mwh: pd.Series) -> DispatchDownModels:
    """Two-stage baseline for real labels: occurrence + positive volume.

    Use chronological train/validation splits outside this function. Never random-split a
    time series when reporting final performance.
    """
    y_occurs = (dispatch_down_mwh > 0).astype(int)
    occurrence = HistGradientBoostingClassifier(max_depth=6, learning_rate=0.05, random_state=42)
    occurrence.fit(X, y_occurs)

    positive = dispatch_down_mwh > 0
    if positive.sum() < 10:
        raise ValueError("Need at least 10 positive dispatch-down intervals to fit volume model.")
    volume = HistGradientBoostingRegressor(max_depth=6, learning_rate=0.05, random_state=42)
    volume.fit(X.loc[positive], dispatch_down_mwh.loc[positive])
    return DispatchDownModels(occurrence=occurrence, volume=volume)


def evaluate(models: DispatchDownModels, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
    p = models.occurrence.predict_proba(X)[:, 1]
    positive_pred = models.volume.predict(X).clip(min=0)
    expected = p * positive_pred
    return {
        "occurrence_pr_auc": average_precision_score((y > 0).astype(int), p),
        "expected_volume_mae_mwh": mean_absolute_error(y, expected),
    }
