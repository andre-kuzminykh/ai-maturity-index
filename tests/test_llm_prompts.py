"""Tests for LLM prompt generation."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.llm_prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, build_user_prompt
from services.scoring import calculate_results
from data.question_bank import QUESTIONS


def _make_answer(question_code, category_code, score, is_unknown=False):
    return {
        "question_code": question_code,
        "category_code": category_code,
        "score": score,
        "is_unknown": is_unknown,
        "option_value": score,
    }


def test_system_prompt_exists():
    assert len(SYSTEM_PROMPT) > 50
    assert "русском" in SYSTEM_PROMPT


def test_user_prompt_template_has_placeholders():
    assert "{total_percent}" in USER_PROMPT_TEMPLATE
    assert "{maturity_level}" in USER_PROMPT_TEMPLATE
    assert "{categories_text}" in USER_PROMPT_TEMPLATE
    assert "Дорожная карта" in USER_PROMPT_TEMPLATE or "дорожн" in USER_PROMPT_TEMPLATE.lower()


def test_build_user_prompt():
    answers = []
    for q in QUESTIONS:
        answers.append(_make_answer(q["code"], q["category"], 3))

    result = calculate_results(answers)
    prompt = build_user_prompt(result, answers, {q["code"]: q for q in QUESTIONS})

    assert "50.0%" in prompt
    assert "AI-Driven" in prompt
    assert "Стратегия" in prompt
    assert len(prompt) > 200


def test_prompt_contains_roadmap_sections():
    """Prompt template should request structured roadmap."""
    assert "Быстрые шаги" in USER_PROMPT_TEMPLATE
    assert "Среднесрочные" in USER_PROMPT_TEMPLATE
    assert "Долгосрочные" in USER_PROMPT_TEMPLATE


def test_prompt_with_unknown_answers():
    answers = []
    for i, q in enumerate(QUESTIONS):
        if i < 5:
            answers.append(_make_answer(q["code"], q["category"], None, is_unknown=True))
        else:
            answers.append(_make_answer(q["code"], q["category"], 4))

    result = calculate_results(answers)
    prompt = build_user_prompt(result, answers, {q["code"]: q for q in QUESTIONS})
    assert "Не знаю" in prompt
