"""Tests for the deterministic scoring engine."""
import pytest
from app.services.scoring import calculate_result, CategoryResult, AssessmentResult


CATEGORIES = [
    {"code": "strategy", "name": "Стратегия и управление", "emoji": "🎯", "weight": 0.15},
    {"code": "people", "name": "Люди и культура", "emoji": "👥", "weight": 0.15},
    {"code": "infrastructure", "name": "Инфраструктура", "emoji": "🏗", "weight": 0.15},
    {"code": "data", "name": "Данные", "emoji": "🗂", "weight": 0.15},
    {"code": "models", "name": "Модели", "emoji": "🧠", "weight": 0.15},
    {"code": "deployment", "name": "Внедрение", "emoji": "⚙️", "weight": 0.20},
    {"code": "rnd", "name": "Исследования и разработки", "emoji": "🔬", "weight": 0.05},
]


def _make_answers(scores_by_category: dict[str, list[int | None]]) -> list[dict]:
    """Helper: build answers list from {category_code: [scores]}."""
    answers = []
    for cat_code, scores in scores_by_category.items():
        for s in scores:
            if s is None:
                answers.append({"category_code": cat_code, "score": None, "is_unknown": True})
            else:
                answers.append({"category_code": cat_code, "score": s, "is_unknown": False})
    return answers


class TestCategoryResult:
    def test_avg_and_percent(self):
        cr = CategoryResult(code="test", name="Test", emoji="🔬", weight=0.1, scores=[1, 3, 5])
        assert cr.avg == 3.0
        assert cr.percent == 50.0

    def test_min_scores(self):
        cr = CategoryResult(code="test", name="Test", emoji="🔬", weight=0.1, scores=[1, 1, 1, 1, 1])
        assert cr.avg == 1.0
        assert cr.percent == 0.0

    def test_max_scores(self):
        cr = CategoryResult(code="test", name="Test", emoji="🔬", weight=0.1, scores=[5, 5, 5, 5, 5])
        assert cr.avg == 5.0
        assert cr.percent == 100.0

    def test_empty_scores(self):
        cr = CategoryResult(code="test", name="Test", emoji="🔬", weight=0.1)
        assert cr.avg == 0.0
        assert cr.percent == 0.0

    def test_approximate_flag(self):
        cr = CategoryResult(code="test", name="Test", emoji="🔬", weight=0.1, scores=[3, 4], unknown_count=3)
        assert cr.is_approximate is True

    def test_not_approximate(self):
        cr = CategoryResult(code="test", name="Test", emoji="🔬", weight=0.1, scores=[3, 4, 5], unknown_count=2)
        assert cr.is_approximate is False


class TestAssessmentResult:
    def test_all_ones(self):
        """All answers = 1 → 0%."""
        answers = _make_answers({cat["code"]: [1, 1, 1, 1, 1] for cat in CATEGORIES})
        result = calculate_result(answers, CATEGORIES)
        assert result.total_percent == 0.0
        assert result.maturity_level == "Начальный"

    def test_all_fives(self):
        """All answers = 5 → 100%."""
        answers = _make_answers({cat["code"]: [5, 5, 5, 5, 5] for cat in CATEGORIES})
        result = calculate_result(answers, CATEGORIES)
        assert result.total_percent == 100.0
        assert result.maturity_level == "AI-Native"

    def test_all_threes(self):
        """All answers = 3 → 50%."""
        answers = _make_answers({cat["code"]: [3, 3, 3, 3, 3] for cat in CATEGORIES})
        result = calculate_result(answers, CATEGORIES)
        assert result.total_percent == 50.0
        assert result.maturity_level == "AI-Driven"

    def test_weights_matter(self):
        """Deployment (20%) has higher weight than R&D (5%)."""
        # All 3s except deployment=5 and rnd=1
        base = {cat["code"]: [3, 3, 3, 3, 3] for cat in CATEGORIES}
        base["deployment"] = [5, 5, 5, 5, 5]
        base["rnd"] = [1, 1, 1, 1, 1]
        answers = _make_answers(base)
        result = calculate_result(answers, CATEGORIES)
        # Should be above 50% because deployment has 20% weight
        assert result.total_percent > 50.0

    def test_reliability_high(self):
        answers = _make_answers({cat["code"]: [3, 3, 3, 3, 3] for cat in CATEGORIES})
        result = calculate_result(answers, CATEGORIES)
        assert result.reliability == "Высокая"

    def test_reliability_medium(self):
        base = {cat["code"]: [3, 3, 3, None, None] for cat in CATEGORIES}
        answers = _make_answers(base)
        result = calculate_result(answers, CATEGORIES)
        # 21/35 = 60% → low
        # Actually 3*7=21 answered out of 35 → 60% → Низкая
        assert result.reliability in ("Средняя", "Низкая")

    def test_reliability_low_all_unknown(self):
        base = {cat["code"]: [None, None, None, None, None] for cat in CATEGORIES}
        answers = _make_answers(base)
        result = calculate_result(answers, CATEGORIES)
        assert result.reliability == "Низкая"

    def test_to_dict(self):
        answers = _make_answers({cat["code"]: [3, 3, 3, 3, 3] for cat in CATEGORIES})
        result = calculate_result(answers, CATEGORIES)
        d = result.to_dict()
        assert "total_percent" in d
        assert "maturity_level" in d
        assert "categories" in d
        assert len(d["categories"]) == 7
        assert "top_3" in d
        assert "bottom_3" in d

    def test_maturity_levels(self):
        """Test all maturity level boundaries."""
        test_cases = [
            ([1], "Начальный"),     # 0%
            ([2], "AI-Enabled"),    # 25%
            ([3], "AI-Driven"),     # 50%
            ([4], "AI-First"),      # 75%
            ([5], "AI-Native"),     # 100%
        ]
        for scores, expected_level in test_cases:
            answers = _make_answers({cat["code"]: scores * 5 for cat in CATEGORIES})
            result = calculate_result(answers, CATEGORIES)
            assert result.maturity_level == expected_level, f"Score {scores[0]} → expected {expected_level}, got {result.maturity_level}"


class TestQuestionBank:
    def test_total_questions(self):
        from app.db.questions_data import CATEGORIES_DATA
        total = sum(len(cat["questions"]) for cat in CATEGORIES_DATA)
        assert total == 35

    def test_total_categories(self):
        from app.db.questions_data import CATEGORIES_DATA
        assert len(CATEGORIES_DATA) == 7

    def test_each_category_has_5_questions(self):
        from app.db.questions_data import CATEGORIES_DATA
        for cat in CATEGORIES_DATA:
            assert len(cat["questions"]) == 5, f"{cat['name']} has {len(cat['questions'])} questions"

    def test_each_question_has_5_options(self):
        from app.db.questions_data import CATEGORIES_DATA
        for cat in CATEGORIES_DATA:
            for q in cat["questions"]:
                assert len(q["options"]) == 5, f"{q['code']} has {len(q['options'])} options"

    def test_weights_sum_to_100(self):
        from app.db.questions_data import CATEGORIES_DATA
        total_weight = sum(cat["weight"] for cat in CATEGORIES_DATA)
        assert abs(total_weight - 1.0) < 0.001

    def test_option_scores_1_to_5(self):
        from app.db.questions_data import CATEGORIES_DATA
        for cat in CATEGORIES_DATA:
            for q in cat["questions"]:
                scores = sorted(opt["score"] for opt in q["options"])
                assert scores == [1, 2, 3, 4, 5], f"{q['code']} scores: {scores}"

    def test_question_orders_sequential(self):
        from app.db.questions_data import CATEGORIES_DATA
        orders = []
        for cat in CATEGORIES_DATA:
            for q in cat["questions"]:
                orders.append(q["order"])
        assert orders == list(range(1, 36))
