"""
ml/train_personas.py — Train persona clustering model.

Uses KMeans to cluster users based on category consumption and reading
behavior, then applies heuristic labels to each cluster. Saves the model
and the label mapping as a .joblib artifact.

Usage:
    python -m ml.train_personas
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ARTIFACTS_DIR = Path(settings.model_artifacts_dir)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

CLUSTER_FEATURES = [
    "total_pageviews",
    "avg_time_on_page_sec",
    "avg_scroll_depth_pct",
    "visit_frequency_weekly",
    "session_count",
    "articles_read_last_7d",
    "newsletter_open_rate",
    "total_paywall_hits",
]

PERSONA_DEFINITIONS = [
    {
        "name": "Sports Fanatic",
        "slug": "sports-fanatic",
        "rule": lambda row: row.get("top_cat_pct", 0) > 0.6 and row.get("top_cat_name") == "Sports",
    },
    {
        "name": "Deep-Dive Tech Reader",
        "slug": "deep-dive-tech-reader",
        "rule": lambda row: row.get("avg_time_on_page_sec", 0) > 120 and row.get("top_cat_pct", 0) > 0.5 and row.get("top_cat_name") == "Technology",
    },
    {
        "name": "Casual Headline Skimmer",
        "slug": "casual-headline-skimmer",
        "rule": lambda row: row.get("avg_time_on_page_sec", 0) < 30 and row.get("avg_scroll_depth_pct", 0) < 30,
    },
    {
        "name": "News Junkie",
        "slug": "news-junkie",
        "rule": lambda row: row.get("visit_frequency_weekly", 0) > 5 and row.get("category_entropy", 0) > 1.5,
    },
    {
        "name": "Weekend Reader",
        "slug": "weekend-reader",
        "rule": lambda row: row.get("visit_frequency_weekly", 0) < 2 and row.get("total_pageviews", 0) > 10,
    },
]


def _compute_category_entropy(cat_dist: dict) -> float:
    """Shannon entropy of category distribution."""
    probs = [v for v in cat_dist.values() if v > 0]
    if not probs:
        return 0.0
    probs = np.array(probs, dtype=float)
    probs = probs / probs.sum()
    return float(-np.sum(probs * np.log2(probs + 1e-10)))


def _assign_persona_label(row: dict) -> tuple[str, str]:
    """Apply heuristic rules to assign a persona name and slug."""
    for persona in PERSONA_DEFINITIONS:
        if persona["rule"](row):
            return persona["name"], persona["slug"]
    return "General Reader", "general-reader"


def _load_data(engine) -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT * FROM public.reader_features WHERE user_id IS NOT NULL", engine
    )
    if df.empty:
        raise ValueError("No feature rows found — run the feature pipeline first")
    return df


def train(n_clusters: int = 6) -> dict:
    """Train KMeans clustering and assign persona labels."""
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url_sync)
    df = _load_data(engine)

    log.info("Training persona model — %d users, %d clusters", len(df), n_clusters)

    X = df[CLUSTER_FEATURES].copy().fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Find optimal k using silhouette score if enough data
    if len(X) >= n_clusters * 3:
        best_k, best_sil = n_clusters, -1
        for k in range(max(2, n_clusters - 2), n_clusters + 3):
            if k >= len(X):
                continue
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X_scaled)
            sil = silhouette_score(X_scaled, labels)
            log.info("  k=%d  silhouette=%.4f", k, sil)
            if sil > best_sil:
                best_k, best_sil = k, sil
        n_clusters = best_k
        log.info("Selected k=%d (silhouette=%.4f)", n_clusters, best_sil)

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster_id"] = model.fit_predict(X_scaled)

    sil_score = silhouette_score(X_scaled, df["cluster_id"]) if len(X) > n_clusters else 0.0

    # Load category names for heuristic labeling
    cat_names = {}
    try:
        cat_df = pd.read_sql("SELECT id, name FROM public.categories", engine)
        cat_names = dict(zip(cat_df["id"], cat_df["name"]))
    except Exception:
        log.warning("Could not load category names")

    # Assign persona labels per user
    persona_assignments = []
    for _, row in df.iterrows():
        cat_dist = row.get("category_distribution") or {}
        if isinstance(cat_dist, str):
            import json
            cat_dist = json.loads(cat_dist)

        top_cat_id = row.get("top_category_id")
        top_cat_pct = max(cat_dist.values()) if cat_dist else 0.0
        top_cat_name = cat_names.get(top_cat_id, "")

        label_input = {
            "avg_time_on_page_sec": row.get("avg_time_on_page_sec", 0),
            "avg_scroll_depth_pct": row.get("avg_scroll_depth_pct", 0),
            "visit_frequency_weekly": row.get("visit_frequency_weekly", 0),
            "total_pageviews": row.get("total_pageviews", 0),
            "top_cat_pct": top_cat_pct,
            "top_cat_name": top_cat_name,
            "category_entropy": _compute_category_entropy(cat_dist),
        }

        name, slug = _assign_persona_label(label_input)
        persona_assignments.append({
            "user_id": row["user_id"],
            "cluster_id": int(row["cluster_id"]),
            "persona_name": name,
            "persona_slug": slug,
            "confidence": round(1.0 - (label_input["category_entropy"] / max(3.0, label_input["category_entropy"])), 4),
            "traits": label_input,
        })

    # Cluster-to-persona label mapping (majority vote per cluster)
    cluster_labels = {}
    for cluster_id in range(n_clusters):
        cluster_personas = [
            p["persona_name"] for p in persona_assignments if p["cluster_id"] == cluster_id
        ]
        if cluster_personas:
            from collections import Counter
            cluster_labels[cluster_id] = Counter(cluster_personas).most_common(1)[0][0]

    version = f"personas_v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
    artifact_path = ARTIFACTS_DIR / f"{version}.joblib"

    artifact = {
        "model": model,
        "scaler": scaler,
        "feature_columns": CLUSTER_FEATURES,
        "model_version": version,
        "n_clusters": n_clusters,
        "silhouette_score": sil_score,
        "cluster_labels": cluster_labels,
        "persona_assignments": persona_assignments,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(df),
    }
    joblib.dump(artifact, artifact_path)
    log.info("Model saved to %s", artifact_path)

    # Write persona assignments to DB
    _persist_personas(engine, persona_assignments, version)

    return {
        "model_version": version,
        "silhouette_score": sil_score,
        "n_clusters": n_clusters,
        "cluster_labels": cluster_labels,
        "artifact_path": str(artifact_path),
    }


def _persist_personas(engine, assignments: list[dict], version: str) -> None:
    """Write persona assignments to reader_personas table."""
    from sqlalchemy import text as sa_text

    with engine.connect() as conn:
        for p in assignments:
            conn.execute(
                sa_text("""
                    INSERT INTO public.reader_personas
                        (user_id, persona_name, persona_slug, cluster_id, confidence, traits, model_version, computed_at)
                    VALUES
                        (:user_id, :persona_name, :persona_slug, :cluster_id, :confidence, :traits::jsonb, :model_version, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        persona_name = EXCLUDED.persona_name,
                        persona_slug = EXCLUDED.persona_slug,
                        cluster_id = EXCLUDED.cluster_id,
                        confidence = EXCLUDED.confidence,
                        traits = EXCLUDED.traits,
                        model_version = EXCLUDED.model_version,
                        computed_at = NOW()
                """),
                {
                    "user_id": str(p["user_id"]),
                    "persona_name": p["persona_name"],
                    "persona_slug": p["persona_slug"],
                    "cluster_id": p["cluster_id"],
                    "confidence": p["confidence"],
                    "traits": str(p["traits"]).replace("'", '"'),
                    "model_version": version,
                },
            )
        conn.commit()
    log.info("Persisted %d persona assignments", len(assignments))


if __name__ == "__main__":
    result = train()
    print(f"\nTraining complete: {result}")
