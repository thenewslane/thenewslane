"""
tests/test_viral_prediction.py — Unit tests for the viral prediction system.

Covers:
  models/feature_engineer.py   (FeatureEngineer, FeatureVector)
  models/linear_scorer.py      (LinearScorer, ScorerResult)
  models/llm_validator.py      (LLMValidator, ValidationResult)
  nodes/viral_prediction_node.py (ViralPredictionNode)

All external I/O is mocked:
  - utils.supabase_client.db  (Supabase)
  - anthropic.Anthropic        (LLM calls)
"""

from __future__ import annotations

from datetime import timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from models.feature_engineer import (
    DEFAULT_CATEGORY_MULTIPLIERS,
    DEFAULT_CATEGORY_MULTIPLIER,
    FeatureEngineer,
    FeatureVector,
)
from models.linear_scorer import DEFAULT_WEIGHTS, LinearScorer, ScorerResult
from models.llm_validator import LLMValidator, ValidationResult
from nodes.collection_node import RawTopic
from nodes.viral_prediction_node import TIER_1_MIN, TIER_2_MIN, TIER_3_MIN, ViralPredictionNode


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_topic(
    keyword: str = "test topic",
    platforms: list[str] | None = None,
    twitter_rank: int | None = 5,
    reddit_score: int | None = 25_000,
    trends_interest: int | None = 80,
    news_count: int = 40,
    raw_rows: list[dict[str, Any]] | None = None,
) -> RawTopic:
    return RawTopic(
        keyword=keyword,
        platforms=platforms or ["twitter", "reddit", "google_trends"],
        twitter_rank=twitter_rank,
        reddit_score=reddit_score,
        trends_interest=trends_interest,
        news_count=news_count,
        raw_rows=raw_rows or [
            {
                "platform": "twitter",
                "topic_keyword": keyword,
                "title": f"{keyword} breaking now",
                "raw_data": {"title": f"{keyword} breaking now"},
            }
        ],
    )


# ---------------------------------------------------------------------------
# FeatureEngineer — cross_platform_score
# ---------------------------------------------------------------------------


def test_feature_engineer_single_platform() -> None:
    topic = _make_topic(platforms=["twitter"])
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic)
    assert fv.cross_platform_score == 1.0


def test_feature_engineer_three_platforms() -> None:
    topic = _make_topic(platforms=["twitter", "reddit", "google_trends"])
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic)
    assert fv.cross_platform_score == 3.0


def test_feature_engineer_four_platforms() -> None:
    topic = _make_topic(platforms=["twitter", "reddit", "google_trends", "google_news"])
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic)
    assert fv.cross_platform_score == 4.0


# ---------------------------------------------------------------------------
# FeatureEngineer — velocity_ratio
# ---------------------------------------------------------------------------


def test_feature_engineer_velocity_default_no_previous() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, previous_batch_data=[])
    assert fv.velocity_ratio == 1.0


def test_feature_engineer_velocity_growing() -> None:
    topic = _make_topic(twitter_rank=1, reddit_score=50_000, trends_interest=100)
    # Previous score much lower → ratio > 1
    prev = [{"signal_score": 10.0, "velocity_ratio": 1.0}]
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, previous_batch_data=prev)
    assert fv.velocity_ratio > 1.0


def test_feature_engineer_velocity_declining() -> None:
    topic = _make_topic(twitter_rank=50, reddit_score=100, trends_interest=5, news_count=0)
    prev = [{"signal_score": 1000.0, "velocity_ratio": 5.0}]
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, previous_batch_data=prev)
    assert fv.velocity_ratio < 1.0


# ---------------------------------------------------------------------------
# FeatureEngineer — acceleration
# ---------------------------------------------------------------------------


def test_feature_engineer_acceleration_default_insufficient_history() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, previous_batch_data=[{"signal_score": 50.0}])
    assert fv.acceleration == 0.0


def test_feature_engineer_acceleration_computed_with_two_batches() -> None:
    topic = _make_topic()
    prev = [
        {"signal_score": 50.0, "velocity_ratio": 1.5},
        {"signal_score": 30.0, "velocity_ratio": 1.0},
    ]
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, previous_batch_data=prev)
    # current velocity - 1.0 (prev batch velocity)
    assert fv.acceleration != 0.0


def test_feature_engineer_acceleration_no_history() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, previous_batch_data=[])
    assert fv.acceleration == 0.0


# ---------------------------------------------------------------------------
# FeatureEngineer — publication_gap_score
# ---------------------------------------------------------------------------


def test_feature_engineer_pub_gap_normal() -> None:
    topic = _make_topic(news_count=48)
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, hours_since_first_article=24.0)
    assert fv.publication_gap_score == pytest.approx(2.0)


def test_feature_engineer_pub_gap_capped_at_10() -> None:
    topic = _make_topic(news_count=10_000)
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, hours_since_first_article=1.0)
    assert fv.publication_gap_score == 10.0


def test_feature_engineer_pub_gap_zero_news() -> None:
    topic = _make_topic(news_count=0)
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic)
    assert fv.publication_gap_score == 0.0


# ---------------------------------------------------------------------------
# FeatureEngineer — sentiment_score
# ---------------------------------------------------------------------------


def test_feature_engineer_sentiment_positive_topic() -> None:
    topic = _make_topic(keyword="amazing breakthrough success")
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic)
    assert 0.0 <= fv.sentiment_score <= 1.0


def test_feature_engineer_sentiment_negative_topic() -> None:
    # Strongly negative text should still yield a positive abs(compound)
    topic = _make_topic(keyword="terrible disaster death tragedy")
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic)
    assert fv.sentiment_score > 0.0


def test_feature_engineer_sentiment_neutral_keyword() -> None:
    topic = _make_topic(keyword="a b c")
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic)
    assert 0.0 <= fv.sentiment_score <= 1.0


# ---------------------------------------------------------------------------
# FeatureEngineer — time_multiplier
# ---------------------------------------------------------------------------


def test_feature_engineer_time_multiplier_peak_hour() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db, patch(
        "models.feature_engineer.datetime"
    ) as mock_dt:
        mock_db.get_config_value.return_value = None
        mock_now = MagicMock()
        mock_now.hour = 13  # 13 UTC is a peak hour
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kwargs: __import__("datetime").datetime(*args, **kwargs)
        fv = FeatureEngineer().compute(topic)
    assert fv.time_multiplier == 1.2


def test_feature_engineer_time_multiplier_off_peak() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db, patch(
        "models.feature_engineer.datetime"
    ) as mock_dt:
        mock_db.get_config_value.return_value = None
        mock_now = MagicMock()
        mock_now.hour = 9  # 9 UTC is off-peak
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kwargs: __import__("datetime").datetime(*args, **kwargs)
        fv = FeatureEngineer().compute(topic)
    assert fv.time_multiplier == 1.0


# ---------------------------------------------------------------------------
# FeatureEngineer — category_multiplier
# ---------------------------------------------------------------------------


def test_feature_engineer_category_entertainment() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, category="entertainment")
    assert fv.category_multiplier == DEFAULT_CATEGORY_MULTIPLIERS["entertainment"]


def test_feature_engineer_category_sports() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, category="sports")
    assert fv.category_multiplier == DEFAULT_CATEGORY_MULTIPLIERS["sports"]


def test_feature_engineer_category_technology() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, category="technology")
    assert fv.category_multiplier == DEFAULT_CATEGORY_MULTIPLIERS["technology"]


def test_feature_engineer_category_unknown_defaults_to_1() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, category="unknown_category")
    assert fv.category_multiplier == DEFAULT_CATEGORY_MULTIPLIER


def test_feature_engineer_category_none_defaults_to_1() -> None:
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        fv = FeatureEngineer().compute(topic, category=None)
    assert fv.category_multiplier == DEFAULT_CATEGORY_MULTIPLIER


def test_feature_engineer_category_from_config_table() -> None:
    """Config table value takes precedence over hard-coded defaults."""
    topic = _make_topic()
    with patch("models.feature_engineer.db") as mock_db:
        mock_db.get_config_value.return_value = {"entertainment": 1.5, "sports": 1.4}
        fv = FeatureEngineer().compute(topic, category="entertainment")
    assert fv.category_multiplier == 1.5


# ---------------------------------------------------------------------------
# LinearScorer
# ---------------------------------------------------------------------------


def _make_fv(
    cross_platform: float = 2.0,
    velocity_ratio: float = 1.0,
    acceleration: float = 0.0,
    publication_gap: float = 2.0,
    sentiment: float = 0.5,
    time_multiplier: float = 1.0,
    category_multiplier: float = 1.0,
) -> FeatureVector:
    return FeatureVector(
        cross_platform_score=cross_platform,
        velocity_ratio=velocity_ratio,
        acceleration=acceleration,
        publication_gap_score=publication_gap,
        sentiment_score=sentiment,
        time_multiplier=time_multiplier,
        category_multiplier=category_multiplier,
    )


def test_linear_scorer_returns_scorer_result() -> None:
    with patch("models.linear_scorer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        result = LinearScorer().score(_make_fv())
    assert isinstance(result, ScorerResult)


def test_linear_scorer_all_zero_features_scores_near_zero() -> None:
    fv = _make_fv(cross_platform=0, velocity_ratio=0, acceleration=0,
                  publication_gap=0, sentiment=0)
    with patch("models.linear_scorer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        result = LinearScorer().score(fv)
    # acceleration=0 → normalised to 0.5 → slight positive; everything else 0
    assert result.raw_score >= 0.0
    assert result.raw_score < 15.0


def test_linear_scorer_all_max_features_scores_near_100() -> None:
    fv = _make_fv(
        cross_platform=4.0,
        velocity_ratio=5.0,
        acceleration=2.0,
        publication_gap=10.0,
        sentiment=1.0,
        time_multiplier=1.2,
        category_multiplier=1.3,
    )
    with patch("models.linear_scorer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        result = LinearScorer().score(fv)
    assert result.raw_score == 100.0  # capped


def test_linear_scorer_score_in_valid_range() -> None:
    with patch("models.linear_scorer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        result = LinearScorer().score(_make_fv())
    assert 0.0 <= result.raw_score <= 100.0


def test_linear_scorer_uses_default_weights_when_config_fails() -> None:
    with patch("models.linear_scorer.db") as mock_db:
        mock_db.get_config_value.side_effect = Exception("DB error")
        scorer = LinearScorer()
        result = scorer.score(_make_fv())
    assert scorer.weights == DEFAULT_WEIGHTS
    assert isinstance(result, ScorerResult)


def test_linear_scorer_loads_custom_weights_from_config() -> None:
    custom_weights = {
        "cross_platform": 0.5,
        "velocity_ratio": 0.2,
        "acceleration":   0.1,
        "publication_gap": 0.1,
        "sentiment":      0.1,
    }
    with patch("models.linear_scorer.db") as mock_db:
        mock_db.get_config_value.return_value = custom_weights
        scorer = LinearScorer()
        result = scorer.score(_make_fv(cross_platform=4.0))
    assert scorer.weights == custom_weights
    assert result.raw_score > 0.0


def test_linear_scorer_time_multiplier_raises_score() -> None:
    base_fv = _make_fv(time_multiplier=1.0)
    peak_fv = _make_fv(time_multiplier=1.2)
    with patch("models.linear_scorer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        scorer = LinearScorer()
        base_result = scorer.score(base_fv)
        peak_result = scorer.score(peak_fv)
    assert peak_result.raw_score >= base_result.raw_score


def test_linear_scorer_category_multiplier_raises_score() -> None:
    base_fv = _make_fv(category_multiplier=1.0)
    ent_fv  = _make_fv(category_multiplier=1.3)
    with patch("models.linear_scorer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        scorer = LinearScorer()
        assert scorer.score(ent_fv).raw_score >= scorer.score(base_fv).raw_score


def test_linear_scorer_weights_used_in_result() -> None:
    with patch("models.linear_scorer.db") as mock_db:
        mock_db.get_config_value.return_value = None
        result = LinearScorer().score(_make_fv())
    assert "cross_platform" in result.weights_used
    assert "velocity_ratio" in result.weights_used


# ---------------------------------------------------------------------------
# LLMValidator — out-of-band scores (no API call)
# ---------------------------------------------------------------------------


def test_llm_validator_score_below_band_passes_through() -> None:
    result = LLMValidator().validate("test", 39.0, "signals")
    assert result.llm_called is False
    assert result.adjusted_score == 39.0
    assert result.llm_verdict is None


def test_llm_validator_score_above_band_passes_through() -> None:
    result = LLMValidator().validate("test", 61.0, "signals")
    assert result.llm_called is False
    assert result.adjusted_score == 61.0


def test_llm_validator_score_at_band_edges_triggers_call() -> None:
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="yes it will keep growing.")]

    with patch("models.llm_validator.anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_msg

        result_low  = LLMValidator().validate("test", 40.0, "signals")
        result_high = LLMValidator().validate("test", 60.0, "signals")

    assert result_low.llm_called is True
    assert result_high.llm_called is True


# ---------------------------------------------------------------------------
# LLMValidator — yes / no parsing
# ---------------------------------------------------------------------------


def _validator_with_response(text: str) -> LLMValidator:
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=text)]
    validator = LLMValidator()
    validator._client = MagicMock()
    validator._client.messages.create.return_value = mock_msg
    return validator


def test_llm_validator_yes_boosts_score() -> None:
    v = _validator_with_response("yes this will definitely go viral in the next few hours.")
    result = v.validate("test topic", 50.0, "some signals")
    assert result.adjusted_score == pytest.approx(63.0)
    assert result.llm_verdict is True
    assert result.llm_confidence == 1.0


def test_llm_validator_no_reduces_score() -> None:
    v = _validator_with_response("no the topic is already fading out.")
    result = v.validate("test topic", 50.0, "some signals")
    assert result.adjusted_score == pytest.approx(37.0)
    assert result.llm_verdict is False
    assert result.llm_confidence == 1.0


def test_llm_validator_yes_capped_at_100() -> None:
    v = _validator_with_response("yes it will keep growing.")
    result = v.validate("test topic", 95.0, "high signals")
    # 95 is above band, so no call
    assert result.adjusted_score == 95.0
    assert result.llm_called is False


def test_llm_validator_no_floored_at_zero() -> None:
    v = _validator_with_response("no it will fade.")
    # Force into band by patching; use a very low score near 40
    result = v.validate("test topic", 40.0, "signals")
    assert result.adjusted_score == pytest.approx(27.0)
    assert result.adjusted_score >= 0.0


def test_llm_validator_ambiguous_response_no_adjustment() -> None:
    v = _validator_with_response("maybe it could go either way.")
    result = v.validate("test topic", 50.0, "signals")
    assert result.adjusted_score == 50.0
    assert result.llm_verdict is None
    assert result.llm_confidence == 0.5


def test_llm_validator_api_error_returns_original_score() -> None:
    validator = LLMValidator()
    validator._client = MagicMock()
    validator._client.messages.create.side_effect = Exception("network timeout")
    result = validator.validate("test topic", 50.0, "signals")
    assert result.adjusted_score == 50.0
    assert result.llm_called is True
    assert result.llm_verdict is None
    assert "API error" in (result.llm_reasoning or "")


def test_llm_validator_reasoning_extracted() -> None:
    v = _validator_with_response("yes this is clearly going viral today.")
    result = v.validate("test topic", 50.0, "signals")
    assert result.llm_reasoning is not None
    assert len(result.llm_reasoning) > 0


# ---------------------------------------------------------------------------
# ViralPredictionNode — tier assignment
# ---------------------------------------------------------------------------


def _mock_node_run(
    score_override: float,
    topic: RawTopic | None = None,
) -> list[dict[str, Any]]:
    """
    Run ViralPredictionNode.run() with all external calls mocked.

    LinearScorer always returns score_override; LLMValidator passes through
    (score not in 40-60 band).
    """
    if topic is None:
        topic = _make_topic()

    fake_topic_row = {"id": "uuid-test-001"}
    fake_pred_row  = {"id": "uuid-pred-001"}

    with (
        patch("nodes.viral_prediction_node.db") as mock_db,
        patch("models.feature_engineer.db") as mock_fe_db,
        patch("models.linear_scorer.db") as mock_ls_db,
    ):
        mock_db.client.table.return_value.select.return_value\
            .eq.return_value.order.return_value.limit.return_value\
            .execute.return_value.data = []
        mock_db.insert_topic.return_value = fake_topic_row
        mock_db.insert_viral_prediction.return_value = fake_pred_row
        mock_fe_db.get_config_value.return_value = None
        mock_ls_db.get_config_value.return_value = None

        node = ViralPredictionNode()
        # Patch LinearScorer.score so it always returns score_override
        with patch.object(
            node._scorer,
            "score",
            return_value=MagicMock(raw_score=score_override),
        ), patch.object(
            node._validator,
            "validate",
            return_value=MagicMock(
                adjusted_score=score_override,
                llm_called=False,
                llm_verdict=None,
                llm_reasoning=None,
                llm_confidence=None,
            ),
        ):
            return node.run("batch_test", [topic])


def test_viral_prediction_node_tier1_score() -> None:
    results = _mock_node_run(score_override=85.0)
    assert len(results) == 1
    assert results[0]["viral_tier"] == 1


def test_viral_prediction_node_tier2_score() -> None:
    results = _mock_node_run(score_override=70.0)
    assert len(results) == 1
    assert results[0]["viral_tier"] == 2


def test_viral_prediction_node_tier3_score() -> None:
    results = _mock_node_run(score_override=55.0)
    assert len(results) == 1
    assert results[0]["viral_tier"] == 3


def test_viral_prediction_node_rejected_below_threshold() -> None:
    results = _mock_node_run(score_override=30.0)
    assert results == []


def test_viral_prediction_node_boundary_tier1_min() -> None:
    results = _mock_node_run(score_override=TIER_1_MIN)
    assert results[0]["viral_tier"] == 1


def test_viral_prediction_node_boundary_tier2_min() -> None:
    results = _mock_node_run(score_override=TIER_2_MIN)
    assert results[0]["viral_tier"] == 2


def test_viral_prediction_node_boundary_tier3_min() -> None:
    results = _mock_node_run(score_override=TIER_3_MIN)
    assert results[0]["viral_tier"] == 3


def test_viral_prediction_node_boundary_just_below_threshold() -> None:
    results = _mock_node_run(score_override=TIER_3_MIN - 0.1)
    assert results == []


# ---------------------------------------------------------------------------
# ViralPredictionNode — sorting and multi-topic behaviour
# ---------------------------------------------------------------------------


def test_viral_prediction_node_sorted_by_score_descending() -> None:
    topics = [
        _make_topic(keyword="topic a", twitter_rank=10),
        _make_topic(keyword="topic b", twitter_rank=1),
        _make_topic(keyword="topic c", twitter_rank=5),
    ]
    scores = [55.0, 90.0, 72.0]

    fake_topic_row = {"id": "uuid-001"}
    call_count = 0

    def _fake_score(fv: Any) -> MagicMock:
        nonlocal call_count
        s = scores[call_count % len(scores)]
        call_count += 1
        return MagicMock(raw_score=s)

    def _fake_validate(name: str, score: float, summary: str) -> MagicMock:
        return MagicMock(
            adjusted_score=score,
            llm_called=False,
            llm_verdict=None,
            llm_reasoning=None,
            llm_confidence=None,
        )

    with (
        patch("nodes.viral_prediction_node.db") as mock_db,
        patch("models.feature_engineer.db") as mock_fe_db,
        patch("models.linear_scorer.db") as mock_ls_db,
    ):
        mock_db.client.table.return_value.select.return_value\
            .eq.return_value.order.return_value.limit.return_value\
            .execute.return_value.data = []
        mock_db.insert_topic.return_value = fake_topic_row
        mock_db.insert_viral_prediction.return_value = {"id": "pred-001"}
        mock_fe_db.get_config_value.return_value = None
        mock_ls_db.get_config_value.return_value = None

        node = ViralPredictionNode()
        with (
            patch.object(node._scorer, "score", side_effect=_fake_score),
            patch.object(node._validator, "validate", side_effect=_fake_validate),
        ):
            results = node.run("batch_sort_test", topics)

    result_scores = [r["score"] for r in results]
    assert result_scores == sorted(result_scores, reverse=True)


def test_viral_prediction_node_empty_input() -> None:
    with (
        patch("nodes.viral_prediction_node.db") as mock_db,
        patch("models.feature_engineer.db"),
        patch("models.linear_scorer.db"),
    ):
        mock_db.client.table.return_value.select.return_value\
            .eq.return_value.order.return_value.limit.return_value\
            .execute.return_value.data = []
        results = ViralPredictionNode().run("batch_empty", [])
    assert results == []


# ---------------------------------------------------------------------------
# ViralPredictionNode — DB persistence
# ---------------------------------------------------------------------------


def test_viral_prediction_node_calls_insert_topic() -> None:
    topic = _make_topic()

    with (
        patch("nodes.viral_prediction_node.db") as mock_db,
        patch("models.feature_engineer.db") as mock_fe_db,
        patch("models.linear_scorer.db") as mock_ls_db,
    ):
        mock_db.client.table.return_value.select.return_value\
            .eq.return_value.order.return_value.limit.return_value\
            .execute.return_value.data = []
        mock_db.insert_topic.return_value = {"id": "topic-uuid"}
        mock_db.insert_viral_prediction.return_value = {"id": "pred-uuid"}
        mock_fe_db.get_config_value.return_value = None
        mock_ls_db.get_config_value.return_value = None

        node = ViralPredictionNode()
        with patch.object(
            node._scorer, "score", return_value=MagicMock(raw_score=75.0)
        ), patch.object(
            node._validator,
            "validate",
            return_value=MagicMock(
                adjusted_score=75.0, llm_called=False, llm_verdict=None,
                llm_reasoning=None, llm_confidence=None,
            ),
        ):
            node.run("batch_db_test", [topic])

    mock_db.insert_topic.assert_called_once()
    insert_args = mock_db.insert_topic.call_args[0][0]
    assert insert_args["batch_id"] == "batch_db_test"
    assert "title" in insert_args
    assert "slug" in insert_args


def test_viral_prediction_node_calls_insert_viral_prediction() -> None:
    topic = _make_topic()

    with (
        patch("nodes.viral_prediction_node.db") as mock_db,
        patch("models.feature_engineer.db") as mock_fe_db,
        patch("models.linear_scorer.db") as mock_ls_db,
    ):
        mock_db.client.table.return_value.select.return_value\
            .eq.return_value.order.return_value.limit.return_value\
            .execute.return_value.data = []
        mock_db.insert_topic.return_value = {"id": "topic-uuid"}
        mock_db.insert_viral_prediction.return_value = {"id": "pred-uuid"}
        mock_fe_db.get_config_value.return_value = None
        mock_ls_db.get_config_value.return_value = None

        node = ViralPredictionNode()
        with patch.object(
            node._scorer, "score", return_value=MagicMock(raw_score=82.0)
        ), patch.object(
            node._validator,
            "validate",
            return_value=MagicMock(
                adjusted_score=82.0, llm_called=False, llm_verdict=None,
                llm_reasoning=None, llm_confidence=None,
            ),
        ):
            node.run("batch_pred_test", [topic])

    mock_db.insert_viral_prediction.assert_called_once()
    pred_args = mock_db.insert_viral_prediction.call_args[0][0]
    assert pred_args["topic_id"] == "topic-uuid"
    assert pred_args["batch_id"] == "batch_pred_test"
    assert "weighted_score" in pred_args
    assert "tier_assigned" in pred_args
    assert pred_args["tier_assigned"] == 1


def test_viral_prediction_node_rejected_topic_still_persisted() -> None:
    """Rejected topics are saved to viral_predictions but excluded from return value."""
    topic = _make_topic()

    with (
        patch("nodes.viral_prediction_node.db") as mock_db,
        patch("models.feature_engineer.db") as mock_fe_db,
        patch("models.linear_scorer.db") as mock_ls_db,
    ):
        mock_db.client.table.return_value.select.return_value\
            .eq.return_value.order.return_value.limit.return_value\
            .execute.return_value.data = []
        mock_db.insert_topic.return_value = {"id": "topic-rej"}
        mock_db.insert_viral_prediction.return_value = {"id": "pred-rej"}
        mock_fe_db.get_config_value.return_value = None
        mock_ls_db.get_config_value.return_value = None

        node = ViralPredictionNode()
        with patch.object(
            node._scorer, "score", return_value=MagicMock(raw_score=20.0)
        ), patch.object(
            node._validator,
            "validate",
            return_value=MagicMock(
                adjusted_score=20.0, llm_called=False, llm_verdict=None,
                llm_reasoning=None, llm_confidence=None,
            ),
        ):
            results = node.run("batch_rej_test", [topic])

    # Not returned in passing list
    assert results == []
    # But still persisted
    mock_db.insert_viral_prediction.assert_called_once()
    pred_args = mock_db.insert_viral_prediction.call_args[0][0]
    assert pred_args["rejected"] is True
    assert pred_args["tier_assigned"] is None


def test_viral_prediction_node_llm_validation_invoked_for_borderline() -> None:
    """LLM should be called for scores in the 40–60 band."""
    topic = _make_topic()

    with (
        patch("nodes.viral_prediction_node.db") as mock_db,
        patch("models.feature_engineer.db") as mock_fe_db,
        patch("models.linear_scorer.db") as mock_ls_db,
    ):
        mock_db.client.table.return_value.select.return_value\
            .eq.return_value.order.return_value.limit.return_value\
            .execute.return_value.data = []
        mock_db.insert_topic.return_value = {"id": "topic-llm"}
        mock_db.insert_viral_prediction.return_value = {"id": "pred-llm"}
        mock_fe_db.get_config_value.return_value = None
        mock_ls_db.get_config_value.return_value = None

        # Simulate a "yes" response boosting 50 → 63
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="yes it is gaining significant attention.")]

        node = ViralPredictionNode()
        with (
            patch.object(node._scorer, "score", return_value=MagicMock(raw_score=50.0)),
            patch.object(node._validator._client.messages, "create", return_value=mock_msg),
        ):
            results = node.run("batch_llm_test", [topic])

    assert len(results) == 1
    # 50 + 13 = 63 → Tier 3
    assert results[0]["score"] == pytest.approx(63.0)
    assert results[0]["viral_tier"] == 3
