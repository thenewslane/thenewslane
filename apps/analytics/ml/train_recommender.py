"""
ml/train_recommender.py — Train article recommendation model.

Combines content-based filtering (category affinity) with collaborative
filtering (user-article interaction matrix) to predict click probability.
Evaluates with Precision@3 and nDCG.

Usage:
    python -m ml.train_recommender
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ARTIFACTS_DIR = Path(settings.model_artifacts_dir)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_interactions(engine) -> pd.DataFrame:
    """Load user-article interaction data from reader_events."""
    query = """
        SELECT
            e.user_id,
            e.topic_id,
            e.category_id,
            t.title,
            t.slug,
            t.viral_score,
            COUNT(*) as interaction_count,
            MAX(CASE WHEN e.event_type = 'click' THEN 1 ELSE 0 END) as clicked,
            AVG(CASE WHEN e.event_type = 'time_on_page'
                THEN (e.metadata->>'seconds')::float ELSE NULL END) as avg_time_sec
        FROM public.reader_events e
        LEFT JOIN public.trending_topics t ON t.id = e.topic_id
        WHERE e.user_id IS NOT NULL AND e.topic_id IS NOT NULL
        GROUP BY e.user_id, e.topic_id, e.category_id, t.title, t.slug, t.viral_score
    """
    return pd.read_sql(query, engine)


def _load_user_features(engine) -> pd.DataFrame:
    """Load user feature vectors for content-based scoring."""
    return pd.read_sql(
        "SELECT user_id, category_distribution, top_category_id FROM public.reader_features WHERE user_id IS NOT NULL",
        engine,
    )


def _build_user_category_matrix(user_features: pd.DataFrame, all_categories: list[int]) -> pd.DataFrame:
    """Build a user x category affinity matrix from category_distribution JSONB."""
    import json

    rows = []
    for _, row in user_features.iterrows():
        dist = row["category_distribution"]
        if isinstance(dist, str):
            dist = json.loads(dist)
        if not isinstance(dist, dict):
            dist = {}

        cat_vec = {f"cat_{c}": dist.get(str(c), 0.0) for c in all_categories}
        cat_vec["user_id"] = row["user_id"]
        rows.append(cat_vec)

    return pd.DataFrame(rows).set_index("user_id").fillna(0)


def _build_interaction_matrix(interactions: pd.DataFrame) -> pd.DataFrame:
    """Build user x topic interaction strength matrix."""
    pivot = interactions.pivot_table(
        index="user_id",
        columns="topic_id",
        values="interaction_count",
        aggfunc="sum",
        fill_value=0,
    )
    return pivot


def _precision_at_k(actual: list, predicted: list, k: int = 3) -> float:
    """Precision@k for a single user."""
    pred_k = predicted[:k]
    if not pred_k:
        return 0.0
    return len(set(pred_k) & set(actual)) / len(pred_k)


def _ndcg_at_k(actual: list, predicted: list, k: int = 3) -> float:
    """Normalized DCG@k for a single user."""
    pred_k = predicted[:k]
    if not pred_k or not actual:
        return 0.0

    dcg = sum(
        1.0 / np.log2(i + 2) for i, item in enumerate(pred_k) if item in actual
    )
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(actual), k)))
    return dcg / idcg if idcg > 0 else 0.0


def train() -> dict:
    """Train hybrid recommender and save artifact."""
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url_sync)

    interactions = _load_interactions(engine)
    if interactions.empty:
        raise ValueError("No interaction data found — ingest events first")

    user_features = _load_user_features(engine)

    log.info(
        "Training recommender — %d interactions, %d users, %d articles",
        len(interactions),
        interactions["user_id"].nunique(),
        interactions["topic_id"].nunique(),
    )

    # Content-based: category affinity
    all_categories = sorted(
        interactions["category_id"].dropna().astype(int).unique().tolist()
    )
    user_cat_matrix = _build_user_category_matrix(user_features, all_categories)

    # Collaborative: user-item interaction matrix
    interaction_matrix = _build_interaction_matrix(interactions)

    # Topic metadata for scoring
    topic_meta = (
        interactions[["topic_id", "category_id", "viral_score", "title", "slug"]]
        .drop_duplicates("topic_id")
        .set_index("topic_id")
    )

    # Compute user similarity via collaborative filtering
    if len(interaction_matrix) > 1 and len(interaction_matrix.columns) > 1:
        user_sim = cosine_similarity(
            normalize(interaction_matrix.values, norm="l2")
        )
        user_sim_df = pd.DataFrame(
            user_sim,
            index=interaction_matrix.index,
            columns=interaction_matrix.index,
        )
    else:
        user_sim_df = pd.DataFrame()

    # Evaluate: leave-one-out on users with 3+ interactions
    precision_scores = []
    ndcg_scores = []

    users_with_enough = interactions.groupby("user_id").filter(
        lambda x: len(x) >= 4
    )["user_id"].unique()

    for uid in users_with_enough[:100]:  # cap evaluation for speed
        user_topics = interactions[interactions["user_id"] == uid]["topic_id"].tolist()
        if len(user_topics) < 4:
            continue

        held_out = user_topics[-1:]
        train_topics = user_topics[:-1]

        # Simple scoring: category affinity + collaborative
        all_topics = topic_meta.index.tolist()
        scores = {}
        for tid in all_topics:
            if tid in train_topics:
                continue
            score = 0.0
            # Category affinity bonus
            cat_id = topic_meta.loc[tid, "category_id"] if tid in topic_meta.index else None
            if cat_id and str(uid) in user_cat_matrix.index:
                col = f"cat_{int(cat_id)}"
                if col in user_cat_matrix.columns:
                    score += float(user_cat_matrix.loc[str(uid), col]) * 0.4
            # Viral score bonus
            vs = topic_meta.loc[tid, "viral_score"] if tid in topic_meta.index else 0
            score += float(vs or 0) * 0.2
            # Collaborative filtering score
            if not user_sim_df.empty and uid in user_sim_df.index:
                similar_users = user_sim_df.loc[uid].nlargest(10).index
                for su in similar_users:
                    if su == uid:
                        continue
                    if su in interaction_matrix.index and tid in interaction_matrix.columns:
                        score += float(interaction_matrix.loc[su, tid]) * 0.01
            scores[tid] = score

        ranked = sorted(scores, key=scores.get, reverse=True)[:3]
        precision_scores.append(_precision_at_k(held_out, ranked, 3))
        ndcg_scores.append(_ndcg_at_k(held_out, ranked, 3))

    mean_precision = float(np.mean(precision_scores)) if precision_scores else 0.0
    mean_ndcg = float(np.mean(ndcg_scores)) if ndcg_scores else 0.0

    log.info("Precision@3: %.4f  nDCG@3: %.4f", mean_precision, mean_ndcg)

    version = f"recommender_v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
    artifact_path = ARTIFACTS_DIR / f"{version}.joblib"

    artifact = {
        "user_cat_matrix": user_cat_matrix,
        "interaction_matrix": interaction_matrix,
        "user_similarity": user_sim_df,
        "topic_metadata": topic_meta,
        "all_categories": all_categories,
        "model_version": version,
        "precision_at_3": mean_precision,
        "ndcg_at_3": mean_ndcg,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_users": int(interactions["user_id"].nunique()),
        "n_articles": int(interactions["topic_id"].nunique()),
    }
    joblib.dump(artifact, artifact_path)
    log.info("Model saved to %s", artifact_path)

    return {
        "model_version": version,
        "precision_at_3": mean_precision,
        "ndcg_at_3": mean_ndcg,
        "artifact_path": str(artifact_path),
    }


if __name__ == "__main__":
    result = train()
    print(f"\nTraining complete: {result}")
