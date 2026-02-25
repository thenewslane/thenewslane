"""
ml/train_propensity.py — Train propensity models (subscribe, churn, register).

Fetches user features from reader_features, trains an XGBClassifier per
propensity type using stratified k-fold cross-validation, evaluates with
ROC-AUC, and saves .joblib artifacts.

Usage:
    python -m ml.train_propensity --type subscribe
    python -m ml.train_propensity --type churn
    python -m ml.train_propensity --type register
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sqlalchemy import create_engine, text
from xgboost import XGBClassifier

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
]


def _load_data(engine, propensity_type: str) -> tuple[pd.DataFrame, pd.Series]:
    """Load features and derive binary labels from reader_features."""
    df = pd.read_sql(
        "SELECT * FROM public.reader_features WHERE user_id IS NOT NULL", engine
    )

    if df.empty:
        raise ValueError("No feature rows found — run the feature pipeline first")

    X = df[FEATURE_COLUMNS].copy()
    X = X.fillna(0)

    if propensity_type == "subscribe":
        y = df["is_subscriber"].astype(int)
    elif propensity_type == "churn":
        # Churn proxy: subscriber with days_since_last_visit > 14
        y = ((df["is_subscriber"]) & (df["days_since_last_visit"] > 14)).astype(int)
    elif propensity_type == "register":
        # Registration proxy: user has a registration date (i.e., they registered)
        y = df["days_since_registration"].notna().astype(int)
    else:
        raise ValueError(f"Unknown propensity type: {propensity_type}")

    return X, y


def train(propensity_type: str) -> dict:
    """Train and save an XGBoost classifier for the given propensity type."""
    engine = create_engine(settings.database_url_sync)
    X, y = _load_data(engine, propensity_type)

    log.info(
        "Training %s model — %d samples, %d positive (%.1f%%)",
        propensity_type,
        len(y),
        y.sum(),
        100 * y.mean(),
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=max((len(y) - y.sum()) / max(y.sum(), 1), 1),
        eval_metric="logloss",
        use_label_encoder=False,
        random_state=42,
    )

    # Stratified k-fold cross-validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        y_prob = model.predict_proba(X_val)[:, 1]

        if len(np.unique(y_val)) > 1:
            auc = roc_auc_score(y_val, y_prob)
            auc_scores.append(auc)
            log.info("  Fold %d ROC-AUC: %.4f", fold, auc)
        else:
            log.warning("  Fold %d: only one class present, skipping AUC", fold)

    # Final model trained on all data
    model.fit(X, y, verbose=False)

    mean_auc = float(np.mean(auc_scores)) if auc_scores else 0.0
    log.info("Mean CV ROC-AUC: %.4f", mean_auc)

    # Feature importances
    importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_.tolist()))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)

    version = f"propensity_{propensity_type}_v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
    artifact_path = ARTIFACTS_DIR / f"{version}.joblib"

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "model_version": version,
        "propensity_type": propensity_type,
        "mean_cv_auc": mean_auc,
        "feature_importances": sorted_imp,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(y),
    }
    joblib.dump(artifact, artifact_path)
    log.info("Model saved to %s", artifact_path)

    return {
        "model_version": version,
        "mean_cv_auc": mean_auc,
        "top_features": sorted_imp[:5],
        "artifact_path": str(artifact_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train propensity model")
    parser.add_argument(
        "--type",
        required=True,
        choices=["subscribe", "churn", "register"],
        help="Propensity type to train",
    )
    args = parser.parse_args()
    result = train(args.type)
    print(f"\nTraining complete: {result}")
