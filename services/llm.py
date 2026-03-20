"""LLM service for generating AI-maturity analysis."""
from __future__ import annotations

import logging

from openai import AsyncOpenAI

import config
from services.llm_prompts import SYSTEM_PROMPT, build_user_prompt
from data.question_bank import QUESTIONS

logger = logging.getLogger(__name__)


FALLBACK_INTERPRETATIONS = {
    "Начальный": "Компания находится на начальном этапе работы с ИИ. Рекомендуется начать с формирования стратегии и пилотных проектов.",
    "AI-Enabled": "Компания делает первые шаги в ИИ. Есть отдельные инициативы, но системного подхода пока нет. Стоит сфокусироваться на стратегии и инфраструктуре.",
    "AI-Driven": "Компания активно внедряет ИИ. Есть работающие процессы и команды. Следующий шаг — масштабирование и углубление интеграции ИИ в бизнес.",
    "AI-First": "Компания строит бизнес вокруг ИИ. Большинство процессов поддерживается ИИ. Фокус — на оптимизации и инновациях.",
    "AI-Native": "Компания — лидер в ИИ-зрелости. ИИ является основой бизнес-модели. Фокус — на поддержании лидерства и развитии R&D.",
}


async def generate_analysis(result: dict, answers: list[dict]) -> str | None:
    """Call LLM to generate analysis. Returns None on failure."""
    if not config.LLM_API_KEY:
        logger.warning("LLM_API_KEY not set, skipping LLM analysis")
        return None

    questions_map = {q["code"]: q for q in QUESTIONS}
    user_prompt = build_user_prompt(result, answers, questions_map)

    try:
        client = AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        response = await client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return None


def get_fallback_analysis(maturity_level: str) -> str:
    """Return a simple fallback when LLM is unavailable."""
    interpretation = FALLBACK_INTERPRETATIONS.get(
        maturity_level,
        "Расширенный анализ временно недоступен.",
    )
    return (
        f"📊 Интерпретация\n{interpretation}\n\n"
        "⚠️ Расширенный анализ (SWOT, рекомендации, дорожная карта) временно недоступен. "
        "Числовой результат сохранен."
    )
