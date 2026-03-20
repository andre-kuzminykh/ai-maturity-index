"""Bot message templates."""

from data.question_bank import QUESTIONS, CATEGORIES, get_category_by_code


def welcome_text() -> str:
    return (
        "🤖 Диагностика AI-зрелости компании\n\n"
        "35 вопросов · 7 категорий · 7–10 минут\n\n"
        "В конце вы получите:\n"
        "• общий индекс зрелости\n"
        "• уровень зрелости\n"
        "• оценки по категориям\n"
        "• SWOT\n"
        "• рекомендации\n"
        "• дорожную карту"
    )


def question_text(question_index: int) -> str:
    """Format a question message with category, progress, text, hint and options."""
    q = QUESTIONS[question_index]
    cat = get_category_by_code(q["category"])

    # Calculate progress
    total = len(QUESTIONS)
    q_num = question_index + 1

    # Category progress
    cat_index = next(i for i, c in enumerate(CATEGORIES) if c["code"] == q["category"])
    cat_questions = [i for i, qq in enumerate(QUESTIONS) if qq["category"] == q["category"]]
    q_in_cat = cat_questions.index(question_index) + 1

    # Format options as plain text
    options_text = "\n".join(q["options"])

    return (
        f"{cat['emoji']} {cat['name']}\n"
        f"Вопрос {q_num} из {total} · "
        f"Категория {cat_index + 1} из {len(CATEGORIES)} · Вопрос {q_in_cat} из 5\n\n"
        f"<b>{q['text']}</b>\n"
        f"<i>{q['hint']}</i>\n\n"
        f"{options_text}"
    )


def abort_confirm_text() -> str:
    return "Остановить диагностику?\nВаш прогресс сохранится."


def restart_confirm_text() -> str:
    return "Начать диагностику заново?\nТекущий прогресс будет удален."


def result_text(result: dict) -> str:
    """Format the deterministic result message."""
    lines = [
        f"📊 Результат диагностики AI-зрелости\n",
        f"Индекс зрелости: <b>{result['total_percent']}%</b>",
        f"Уровень: <b>{result['maturity_level']}</b>",
        f"Надежность: {result['reliability']}",
        "",
        "Категории:",
    ]

    for c in result["categories"]:
        tentative = " ≈" if c.get("tentative") else ""
        lines.append(f"  {c['emoji']} {c['name']} — {c['percent']}%{tentative}")

    lines.append("")
    lines.append("💪 Сильные стороны: " + ", ".join(
        f"{s['name']}" for s in result["strengths"]
    ))
    lines.append("📈 Зоны роста: " + ", ".join(
        f"{w['name']}" for w in result["weaknesses"]
    ))

    return "\n".join(lines)


def progress_text(current: int, total: int) -> str:
    return f"Прогресс сохранен. Вы ответили на {current} из {total} вопросов."
