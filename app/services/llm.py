"""LLM service — called ONLY after deterministic scoring is complete.

LLM does NOT influence scores, weights, or maturity level.
It provides: interpretation, SWOT, recommendations, roadmap.
"""
from __future__ import annotations

import logging
import httpx

from app.config import settings
from app.services.scoring import AssessmentResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — эксперт по ИИ-трансформации компаний. Тебе предоставлены результаты диагностики ИИ-зрелости компании.

ПРАВИЛА:
- Ты НЕ можешь менять баллы, веса или уровень зрелости.
- Ты анализируешь только уже посчитанный результат.
- Пиши кратко, по делу, без воды.
- Используй русский язык.
- Общий объём ответа — не более 1500 символов.

Верни ответ СТРОГО в следующем формате (markdown):

**Интерпретация**
(2-3 предложения о текущем состоянии)

**SWOT-анализ**
S: (1-2 сильные стороны)
W: (1-2 слабые стороны)
O: (1-2 возможности)
T: (1-2 риска)

**Рекомендации**
(3-4 конкретных действия)

**Roadmap**
Сейчас: ...
1-3 месяца: ...
3-6 месяцев: ...
"""


def _build_user_prompt(result: AssessmentResult) -> str:
    cats_text = "\n".join(
        f"- {c.emoji} {c.name}: {c.percent}% (avg {c.avg:.1f}/5)"
        + (" ⚠️ ориентировочно" if c.is_approximate else "")
        for c in result.categories
    )
    top = ", ".join(f"{c.emoji} {c.name}" for c in result.top_categories)
    bottom = ", ".join(f"{c.emoji} {c.name}" for c in result.bottom_categories)

    return f"""Результаты диагностики ИИ-зрелости:

Общий индекс: {result.total_percent}%
Уровень зрелости: {result.maturity_level}
Надёжность: {result.reliability}
Роль: {result.user_role or 'не указана'}

Категории:
{cats_text}

Сильные стороны (топ-3): {top}
Зоны роста (топ-3): {bottom}
"""


async def get_llm_analysis(result: AssessmentResult) -> dict[str, str]:
    """Call LLM API and return analysis sections.

    Returns dict with keys: summary, swot, recommendations, roadmap.
    On failure returns empty dict.
    """
    if not settings.llm_api_key:
        logger.warning("LLM API key not configured, skipping analysis")
        return {}

    user_prompt = _build_user_prompt(result)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.llm_api_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.4,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return _parse_llm_response(content)
    except Exception:
        logger.exception("LLM call failed")
        return {}


def _parse_llm_response(text: str) -> dict[str, str]:
    """Parse structured LLM response into sections."""
    sections = {
        "summary": "",
        "swot": "",
        "recommendations": "",
        "roadmap": "",
    }

    current_key = None
    current_lines: list[str] = []
    section_markers = {
        "интерпретация": "summary",
        "swot": "swot",
        "рекомендации": "recommendations",
        "roadmap": "roadmap",
    }

    for line in text.split("\n"):
        stripped = line.strip().lower().replace("**", "").replace("-", "").strip()
        matched = False
        for marker, key in section_markers.items():
            if marker in stripped and len(stripped) < 40:
                if current_key and current_lines:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = key
                current_lines = []
                matched = True
                break
        if not matched and current_key is not None:
            current_lines.append(line)

    if current_key and current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections
