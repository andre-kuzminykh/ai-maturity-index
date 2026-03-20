"""Tests for the scoring engine."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.scoring import calculate_results, get_maturity_level, get_reliability


def _make_answer(question_code, category_code, score, is_unknown=False):
    return {
        "question_code": question_code,
        "category_code": category_code,
        "score": score,
        "is_unknown": is_unknown,
        "option_value": score,
    }


def test_maturity_levels():
    assert get_maturity_level(0) == "Начальный"
    assert get_maturity_level(10) == "Начальный"
    assert get_maturity_level(20) == "Начальный"
    assert get_maturity_level(21) == "AI-Enabled"
    assert get_maturity_level(40) == "AI-Enabled"
    assert get_maturity_level(50) == "AI-Driven"
    assert get_maturity_level(70) == "AI-First"
    assert get_maturity_level(90) == "AI-Native"
    assert get_maturity_level(100) == "AI-Native"


def test_reliability():
    assert get_reliability(0) == "Высокая"
    assert get_reliability(3) == "Высокая"
    assert get_reliability(4) == "Средняя"
    assert get_reliability(8) == "Средняя"
    assert get_reliability(9) == "Низкая"
    assert get_reliability(20) == "Низкая"


def test_all_fives():
    """All answers are 5 → 100% index."""
    answers = []
    from data.question_bank import QUESTIONS
    for q in QUESTIONS:
        answers.append(_make_answer(q["code"], q["category"], 5))

    result = calculate_results(answers)
    assert result["total_percent"] == 100.0
    assert result["maturity_level"] == "AI-Native"
    assert result["reliability"] == "Высокая"
    assert len(result["categories"]) == 7


def test_all_ones():
    """All answers are 1 → 0% index."""
    answers = []
    from data.question_bank import QUESTIONS
    for q in QUESTIONS:
        answers.append(_make_answer(q["code"], q["category"], 1))

    result = calculate_results(answers)
    assert result["total_percent"] == 0.0
    assert result["maturity_level"] == "Начальный"


def test_all_threes():
    """All answers are 3 → 50% index."""
    answers = []
    from data.question_bank import QUESTIONS
    for q in QUESTIONS:
        answers.append(_make_answer(q["code"], q["category"], 3))

    result = calculate_results(answers)
    assert result["total_percent"] == 50.0
    assert result["maturity_level"] == "AI-Driven"


def test_unknown_answers_reduce_reliability():
    """Many unknown answers → low reliability."""
    answers = []
    from data.question_bank import QUESTIONS
    for i, q in enumerate(QUESTIONS):
        if i < 10:
            answers.append(_make_answer(q["code"], q["category"], None, is_unknown=True))
        else:
            answers.append(_make_answer(q["code"], q["category"], 3))

    result = calculate_results(answers)
    assert result["reliability"] == "Низкая"
    assert result["unknown_count"] == 10


def test_strengths_and_weaknesses():
    """Results should include 3 strengths and 3 weaknesses."""
    answers = []
    from data.question_bank import QUESTIONS
    for q in QUESTIONS:
        answers.append(_make_answer(q["code"], q["category"], 3))

    result = calculate_results(answers)
    assert len(result["strengths"]) == 3
    assert len(result["weaknesses"]) == 3


def test_mixed_scores():
    """Mixed scores produce correct weighted average."""
    answers = []
    from data.question_bank import QUESTIONS, CATEGORIES
    # strategy=5, people=1, rest=3
    for q in QUESTIONS:
        if q["category"] == "strategy":
            answers.append(_make_answer(q["code"], q["category"], 5))
        elif q["category"] == "people":
            answers.append(_make_answer(q["code"], q["category"], 1))
        else:
            answers.append(_make_answer(q["code"], q["category"], 3))

    result = calculate_results(answers)
    # strategy category should be 100%
    strat = next(c for c in result["categories"] if c["code"] == "strategy")
    assert strat["percent"] == 100.0
    # people category should be 0%
    ppl = next(c for c in result["categories"] if c["code"] == "people")
    assert ppl["percent"] == 0.0
    # Total should be between 0 and 100
    assert 0 < result["total_percent"] < 100


def test_tentative_category():
    """Category with fewer than 3 valid answers is tentative."""
    from data.question_bank import QUESTIONS
    answers = []
    strategy_count = 0
    for q in QUESTIONS:
        if q["category"] == "strategy" and strategy_count < 3:
            answers.append(_make_answer(q["code"], q["category"], None, is_unknown=True))
            strategy_count += 1
        else:
            answers.append(_make_answer(q["code"], q["category"], 3))

    result = calculate_results(answers)
    strat = next(c for c in result["categories"] if c["code"] == "strategy")
    assert strat["tentative"] is True


def test_empty_answers():
    """No answers at all → 0%."""
    result = calculate_results([])
    assert result["total_percent"] == 0.0
    assert result["maturity_level"] == "Начальный"
