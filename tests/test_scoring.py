"""Tests for deterministic scoring logic."""

from bot.questions import CATEGORIES, QUESTIONS
from bot.scoring import calculate_results, _maturity_level


def _make_answers(score: int) -> list[dict]:
    """Create answers with the same score for all 35 questions."""
    return [{"question_id": q.id, "score": score} for q in QUESTIONS]


def test_all_ones_gives_zero_percent():
    result = calculate_results(_make_answers(1))
    assert result["total_percent"] == 0.0
    assert result["maturity_level"] == "Начальный"


def test_all_fives_gives_100_percent():
    result = calculate_results(_make_answers(5))
    assert result["total_percent"] == 100.0
    assert result["maturity_level"] == "AI-Native"


def test_all_threes_gives_50_percent():
    result = calculate_results(_make_answers(3))
    assert result["total_percent"] == 50.0
    assert result["maturity_level"] == "AI-Driven"


def test_maturity_levels():
    assert _maturity_level(0) == "Начальный"
    assert _maturity_level(20) == "Начальный"
    assert _maturity_level(20.1) == "AI-Enabled"
    assert _maturity_level(40) == "AI-Enabled"
    assert _maturity_level(40.1) == "AI-Driven"
    assert _maturity_level(60) == "AI-Driven"
    assert _maturity_level(60.1) == "AI-First"
    assert _maturity_level(80) == "AI-First"
    assert _maturity_level(80.1) == "AI-Native"
    assert _maturity_level(100) == "AI-Native"


def test_weights_sum_to_one():
    total = sum(c.weight for c in CATEGORIES)
    assert abs(total - 1.0) < 1e-9


def test_35_questions_7_categories():
    assert len(QUESTIONS) == 35
    assert len(CATEGORIES) == 7
    for cat in CATEGORIES:
        cat_qs = [q for q in QUESTIONS if q.category_code == cat.code]
        assert len(cat_qs) == 5, f"{cat.code} has {len(cat_qs)} questions, expected 5"


def test_each_question_has_5_options():
    for q in QUESTIONS:
        assert len(q.options) == 5, f"Q{q.id} has {len(q.options)} options"
        scores = [o.score for o in q.options]
        assert scores == [1, 2, 3, 4, 5], f"Q{q.id} scores: {scores}"


def test_result_has_3_strong_and_3_weak_zones():
    result = calculate_results(_make_answers(3))
    assert len(result["strong_zones"]) == 3
    assert len(result["weak_zones"]) == 3


def test_result_has_recommendations():
    result = calculate_results(_make_answers(2))
    assert len(result["recommendations"]) == 3
    for rec in result["recommendations"]:
        assert rec["category"]
        assert rec["text"]
