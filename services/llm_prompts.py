"""
LLM-промпты для генерации анализа AI-maturity.
Редактируйте этот файл, чтобы изменить поведение LLM.
"""

SYSTEM_PROMPT = """Ты — эксперт по цифровой трансформации и внедрению ИИ в компаниях.
Тебе дают результаты диагностики AI-зрелости компании.
Твоя задача — дать краткий, конкретный и полезный анализ.

Правила:
- Пиши на русском языке.
- Будь кратким и конкретным.
- Не повторяй числовые результаты — они уже показаны пользователю.
- Не придумывай факты о компании.
- Не используй маркетинговый язык и воду.
- Давай практичные, применимые советы.
- Формат ответа — текст с эмодзи-заголовками, без markdown-разметки.
"""

USER_PROMPT_TEMPLATE = """Результаты диагностики AI-зрелости компании:

Общий индекс: {total_percent}%
Уровень зрелости: {maturity_level}
Надежность результата: {reliability}

Результаты по категориям:
{categories_text}

Сильные стороны: {strengths_text}
Зоны роста: {weaknesses_text}

Ответы пользователя:
{answers_text}

Дай анализ строго в следующем формате:

📊 Интерпретация
Краткая оценка текущего состояния AI-зрелости (2-3 предложения).

📋 SWOT-анализ
S (сильные стороны): 1-2 пункта
W (слабые стороны): 1-2 пункта
O (возможности): 1-2 пункта
T (угрозы): 1-2 пункта

💡 Рекомендации
3-5 конкретных прикладных рекомендаций.

🗺 Дорожная карта зрелости

🚀 Быстрые шаги (сейчас):
- Конкретные действия, которые можно начать немедленно по самым слабым категориям.

📅 Среднесрочные (1-3 месяца):
- Системные улучшения: процессы, команды, инфраструктура.
- Привязка к конкретным категориям зрелости, которые нужно подтянуть.

🎯 Долгосрочные (3-6 месяцев):
- Стратегические инициативы для перехода на следующий уровень зрелости.
- Целевой уровень зрелости и что нужно для его достижения.
"""


def build_user_prompt(result: dict, answers: list[dict], questions_map: dict) -> str:
    """Build the user prompt from assessment results."""
    categories_text = "\n".join(
        f"  {c['emoji']} {c['name']}: {c['percent']}%"
        + (" (ориентировочно)" if c.get("tentative") else "")
        for c in result["categories"]
    )

    strengths_text = ", ".join(
        f"{s['emoji']} {s['name']} ({s['percent']}%)" for s in result["strengths"]
    )
    weaknesses_text = ", ".join(
        f"{w['emoji']} {w['name']} ({w['percent']}%)" for w in result["weaknesses"]
    )

    answers_lines = []
    for ans in answers:
        q = questions_map.get(ans["question_code"])
        if not q:
            continue
        if ans["is_unknown"]:
            answers_lines.append(f"  {q['text']} → Не знаю")
        else:
            idx = (ans["score"] or 1) - 1
            answers_lines.append(f"  {q['text']} → {q['options'][idx]}")
    answers_text = "\n".join(answers_lines)

    return USER_PROMPT_TEMPLATE.format(
        total_percent=result["total_percent"],
        maturity_level=result["maturity_level"],
        reliability=result["reliability"],
        categories_text=categories_text,
        strengths_text=strengths_text,
        weaknesses_text=weaknesses_text,
        answers_text=answers_text,
    )
