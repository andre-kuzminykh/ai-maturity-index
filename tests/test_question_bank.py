"""Tests for the question bank structure."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.question_bank import CATEGORIES, QUESTIONS, get_category_by_code, get_questions_by_category


def test_total_questions():
    assert len(QUESTIONS) == 35


def test_categories_count():
    assert len(CATEGORIES) == 7


def test_five_questions_per_category():
    for cat in CATEGORIES:
        qs = get_questions_by_category(cat["code"])
        assert len(qs) == 5, f"Category {cat['code']} has {len(qs)} questions, expected 5"


def test_weights_sum_to_one():
    total = sum(c["weight"] for c in CATEGORIES)
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"


def test_each_question_has_required_fields():
    for q in QUESTIONS:
        assert "code" in q
        assert "category" in q
        assert "text" in q
        assert "hint" in q
        assert "options" in q
        assert "buttons" in q
        assert len(q["options"]) == 5, f"Question {q['code']} has {len(q['options'])} options"
        assert len(q["buttons"]) == 5, f"Question {q['code']} has {len(q['buttons'])} buttons"


def test_unique_codes():
    codes = [q["code"] for q in QUESTIONS]
    assert len(codes) == len(set(codes)), "Duplicate question codes found"


def test_all_categories_valid():
    valid_codes = {c["code"] for c in CATEGORIES}
    for q in QUESTIONS:
        assert q["category"] in valid_codes, f"Question {q['code']} has invalid category {q['category']}"


def test_get_category_by_code():
    cat = get_category_by_code("strategy")
    assert cat is not None
    assert cat["name"] == "Стратегия и управление"
    assert get_category_by_code("nonexistent") is None
