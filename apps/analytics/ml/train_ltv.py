"""
ml/train_ltv.py — Train predicted Lifetime Value (pLTV) regression model.

Forecasts expected 12-month revenue per user based on behavioral features.
Uses XGBRegressor with k-fold cross-validation and RMSE/MAE evaluation.

Usage:
    python -m ml.train_ltv
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import KFold
from xgboost import XGBRegressor

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ARTIFACTS_DIR = Path(settings.model_artifacts_dir)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLUMNS = [
    "session_count",
    "total_pageviews",
    "articles_read_last_7d",
    "articles_read_last_30d",
    "avg_time_on_page_sec",
    "avg_scroll_depth_pct",
    "newsletter_open_rate",
    "total_paywall_hits",
    "total_shares",
    "days_since_registration",
    "days_since_last_visit",
    "visit_frequency_weekly",
    "is_subscriber",
]

# Revenue assumptions for LTV target derivation
MONTHLY_SUB_REVENUE = 9.99
AD_RPM = 3.50  # revenue per 1000 ad impressions
AVG_ADS_PER_PAGEVIEW = 2


def _load_data(engine) -> tuple[pd.DataFrame, pd.Series]:
    """Load features and compute a synthetic LTV target."""
    df = pd.read_sql(
        "SELECT * FROM public.reader_features WHERE user_id IS NOT NULL", engine
    )

    if df.empty:
        raise ValueError("No feature rows found — run the feature pipeline first")

    X = df[FEATURE_COLUMNS].copy()
    X["is_subscriber"] = X["is_subscriber"].astype(int)
    X = X.fillna(0)

    # LTV = projected subscription revenue + projected ad revenue (12 months)
    sub_revenue_12m = df["is_subscriber"].astype(float) * MONTHLY_SUB_REVENUE * 12

    weekly_pvs = df["visit_frequency_weekly"].fillna(0) * df["total_pageviews"].fillna(0) / df["session_count"].replace(0, 1)
    monthly_pvs = weekly_pvs * 4.33
    ad_revenue_12m = monthly_pvs * AVG_ADS_PER_PAGEVIEW * AD_RPM / 1000 * 12

    y = (sub_revenue_12m + ad_revenue_12m).clip(lower=0).round(2)

    return X, y


def train() -> dict:
    """Train and save XGBRegressor for LTV prediction."""
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url_sync)
    X, y = _load_data(engine)

    log.info("Training LTV model — %d samples, mean LTV=%.2f", len(y), y.mean())

    model = XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    rmse_scores = []
    mae_scores = []

    for fold, (train_idx, val_idx) in enumerate(kf.split(X, y), 1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        y_pred = model.predict(X_val)

        rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))
        mae = float(mean_absolute_error(y_val, y_pred))
        rmse_scores.append(rmse)
        mae_scores.append(mae)
        log.info("  Fold %d RMSE: %.4f  MAE: %.4f", fold, rmse, mae)

    # Final model on all data
    model.fit(X, y, verbose=False)

    mean_rmse = float(np.mean(rmse_scores))
    mean_mae = float(np.mean(mae_scores))
    log.info("Mean CV RMSE: %.4f  MAE: %.4f", mean_rmse, mean_mae)

    importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)

    version = f"ltv_v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
    artifact_path = ARTIFACTS_DIR / f"{version}.joblib"

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "model_version": version,
        "mean_cv_rmse": mean_rmse,
        "mean_cv_mae": mean_mae,
        "feature_importances": sorted_imp,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(y),
        "revenue_params": {
            "monthly_sub_revenue": MONTHLY_SUB_REVENUE,
            "ad_rpm": AD_RPM,
            "avg_ads_per_pageview": AVG_ADS_PER_PAGEVIEW,
        },
    }
    joblib.dump(artifact, artifact_path)
    log.info("Model saved to %s", artifact_path)

    return {
        "model_version": version,
        "mean_cv_rmse": mean_rmse,
        "mean_cv_mae": mean_mae,
        "top_features": sorted_imp[:5],
        "artifact_path": str(artifact_path),
    }


if __name__ == "__main__":
    result = train()
    print(f"\nTraining complete: {result}")
