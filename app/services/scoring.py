"""Deterministic scoring engine.

LLM has NO influence on scores, weights, or maturity level.
"""
from __future__ import annotations
from dataclasses import dataclass, field


MATURITY_LEVELS = [
    (0, 20, "Начальный"),
    (21, 40, "AI-Enabled"),
    (41, 60, "AI-Driven"),
    (61, 80, "AI-First"),
    (81, 100, "AI-Native"),
]

FALLBACK_INTERPRETATIONS = {
    "Начальный": "Компания находится на начальном этапе ИИ-зрелости. ИИ используется фрагментарно, без стратегии и системного подхода.",
    "AI-Enabled": "Компания начала использовать ИИ в отдельных задачах. Есть первые инициативы, но системного внедрения пока нет.",
    "AI-Driven": "ИИ встроен в ключевые процессы компании. Есть стратегия, команды и метрики, но зрелость неравномерна.",
    "AI-First": "ИИ является ключевым элементом операционной модели. Большинство процессов усилены или управляются ИИ.",
    "AI-Native": "Компания полностью построена вокруг ИИ. ИИ — основа стратегии, операций и бизнес-модели.",
}


@dataclass
class CategoryResult:
    code: str
    name: str
    emoji: str
    weight: float
    scores: list[int] = field(default_factory=list)
    unknown_count: int = 0

    @property
    def valid_count(self) -> int:
        return len(self.scores)

    @property
    def total_questions(self) -> int:
        return self.valid_count + self.unknown_count

    @property
    def avg(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores) / len(self.scores)

    @property
    def percent(self) -> float:
        """Normalize 1-5 → 0-100."""
        if not self.scores:
            return 0.0
        return round(((self.avg - 1) / 4) * 100, 1)

    @property
    def is_approximate(self) -> bool:
        """Category result is approximate if less than 3 valid answers."""
        return self.valid_count < 3


@dataclass
class AssessmentResult:
    categories: list[CategoryResult]
    user_role: str | None = None

    @property
    def weighted_avg(self) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for cat in self.categories:
            if cat.valid_count > 0:
                weighted_sum += cat.avg * cat.weight
                total_weight += cat.weight
        if total_weight == 0:
            return 0.0
        return weighted_sum / total_weight

    @property
    def total_percent(self) -> float:
        return round(((self.weighted_avg - 1) / 4) * 100, 1)

    @property
    def maturity_level(self) -> str:
        pct = self.total_percent
        for low, high, name in MATURITY_LEVELS:
            if low <= pct <= high:
                return name
        return MATURITY_LEVELS[-1][2]

    @property
    def total_unknown(self) -> int:
        return sum(c.unknown_count for c in self.categories)

    @property
    def total_answered(self) -> int:
        return sum(c.valid_count for c in self.categories)

    @property
    def total_questions(self) -> int:
        return sum(c.total_questions for c in self.categories)

    @property
    def reliability(self) -> str:
        if self.total_questions == 0:
            return "Низкая"
        ratio = self.total_answered / self.total_questions
        if ratio >= 0.9:
            return "Высокая"
        if ratio >= 0.7:
            return "Средняя"
        return "Низкая"

    @property
    def top_categories(self) -> list[CategoryResult]:
        scored = [c for c in self.categories if c.valid_count > 0]
        return sorted(scored, key=lambda c: c.percent, reverse=True)[:3]

    @property
    def bottom_categories(self) -> list[CategoryResult]:
        scored = [c for c in self.categories if c.valid_count > 0]
        return sorted(scored, key=lambda c: c.percent)[:3]

    @property
    def fallback_interpretation(self) -> str:
        return FALLBACK_INTERPRETATIONS.get(self.maturity_level, "")

    def to_dict(self) -> dict:
        return {
            "total_percent": self.total_percent,
            "maturity_level": self.maturity_level,
            "reliability": self.reliability,
            "weighted_avg": round(self.weighted_avg, 2),
            "total_answered": self.total_answered,
            "total_unknown": self.total_unknown,
            "categories": [
                {
                    "code": c.code,
                    "name": c.name,
                    "emoji": c.emoji,
                    "percent": c.percent,
                    "avg": round(c.avg, 2),
                    "valid_count": c.valid_count,
                    "unknown_count": c.unknown_count,
                    "is_approximate": c.is_approximate,
                }
                for c in self.categories
            ],
            "top_3": [c.code for c in self.top_categories],
            "bottom_3": [c.code for c in self.bottom_categories],
        }


def calculate_result(
    answers: list[dict],
    categories: list[dict],
) -> AssessmentResult:
    """Calculate deterministic assessment result.

    Args:
        answers: list of {"category_code", "score"|None, "is_unknown"}
        categories: list of {"code", "name", "emoji", "weight"}
    """
    cat_map: dict[str, CategoryResult] = {}
    for cat in categories:
        cat_map[cat["code"]] = CategoryResult(
            code=cat["code"],
            name=cat["name"],
            emoji=cat["emoji"],
            weight=cat["weight"],
        )

    for ans in answers:
        cat_code = ans["category_code"]
        cr = cat_map.get(cat_code)
        if cr is None:
            continue
        if ans.get("is_unknown"):
            cr.unknown_count += 1
        elif ans.get("score") is not None:
            cr.scores.append(ans["score"])

    ordered = sorted(cat_map.values(), key=lambda c: next(
        (cat["weight"] for cat in categories if cat["code"] == c.code), 0
    ))
    # Keep original order from categories list
    ordered = [cat_map[cat["code"]] for cat in categories if cat["code"] in cat_map]

    return AssessmentResult(categories=ordered)
