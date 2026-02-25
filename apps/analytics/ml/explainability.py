"""
ml/explainability.py — Feature importance extraction for prediction explanations.

Returns the top-N features driving a specific prediction, with direction
(positive/negative contribution). Uses XGBoost's built-in feature_importances_
for global importance, and per-instance contribution via predict output margins.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def get_top_feature_importances(
    model,
    feature_names: list[str],
    feature_values: np.ndarray,
    top_n: int = 3,
) -> list[dict[str, Any]]:
    """
    Extract top-N feature importances for a single prediction.

    Uses global feature_importances_ weighted by the actual feature values
    to determine which features most influenced this particular prediction.
    Direction is inferred from the sign of the feature value relative to the
    training mean (approximated by whether the value is above/below zero after
    standardization).
    """
    importances = model.feature_importances_

    if len(importances) != len(feature_names):
        return []

    weighted = importances * np.abs(feature_values.flatten())

    top_indices = np.argsort(weighted)[::-1][:top_n]

    result = []
    for idx in top_indices:
        val = float(feature_values.flatten()[idx])
        result.append({
            "name": feature_names[idx],
            "importance": round(float(weighted[idx]), 4),
            "direction": "positive" if val > 0 else "negative",
        })

    return result


def get_global_feature_importances(
    model, feature_names: list[str], top_n: int = 5
) -> list[dict[str, float]]:
    """Return top-N global feature importances from the trained model."""
    importances = model.feature_importances_
    pairs = sorted(
        zip(feature_names, importances.tolist()),
        key=lambda x: x[1],
        reverse=True,
    )
    return [{"name": n, "importance": round(v, 4)} for n, v in pairs[:top_n]]
