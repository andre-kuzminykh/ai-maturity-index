"""Message texts for the bot."""
from html import escape as html_escape
from app.services.scoring import AssessmentResult

WELCOME_TEXT = """🤖 <b>Диагностика ИИ-зрелости компании</b>

35 вопросов · 7 категорий · 7–10 минут

В конце вы получите:
• общий индекс зрелости
• оценки по 7 категориям
• SWOT-анализ
• рекомендации
• краткий roadmap роста"""

ROLE_TEXT = "👤 <b>Ваша роль в компании?</b>"

STOP_CONFIRM_TEXT = "Остановить диагностику? Ваш прогресс сохранится."

RESTART_CONFIRM_TEXT = "Начать диагностику заново? Текущий прогресс будет удалён."

LLM_UNAVAILABLE_TEXT = "\n\n<i>Расширенный анализ временно недоступен. Числовой результат сохранён.</i>"

CONTACT_TEXT = """📞 <b>Оставить контакты</b>

Отправьте ваш email или телефон — мы свяжемся с вами для консультации."""

CONSULT_TEXT = """💬 <b>Запрос на консультацию</b>

Мы получили ваш запрос. Наш эксперт свяжется с вами в ближайшее время.

Если хотите ускорить процесс — отправьте ваш email или телефон."""


def format_question(
    category_emoji: str,
    category_name: str,
    question_order: int,
    total_questions: int,
    category_order: int,
    total_categories: int,
    question_in_category: int,
    questions_in_category: int,
    question_text: str,
    explanation: str,
    options: list[dict],
) -> str:
    """Format question screen message."""
    options_text = "\n".join(
        f"{html_escape(opt['label_short'])}  {html_escape(opt['text_full'])}" for opt in options
    )

    return (
        f"{category_emoji} <b>{category_name}</b>\n"
        f"<b>Вопрос {question_order} из {total_questions}</b>\n"
        f"Категория {category_order} из {total_categories} · "
        f"Вопрос {question_in_category} из {questions_in_category}\n\n"
        f"<b>{question_text}</b>\n"
        f"<i>{explanation}</i>\n\n"
        f"{options_text}"
    )


def format_category_complete(
    category_emoji: str,
    category_name: str,
    answered: int,
    total: int,
) -> str:
    remaining = total - answered
    return (
        f"✅ <b>Категория завершена: {category_name}</b>\n\n"
        f"Вы ответили на {answered} из {total} вопросов\n"
        f"Осталось {remaining} вопросов"
    )


def format_results_brief(result: AssessmentResult) -> str:
    """Format the brief deterministic results (Layer 1)."""
    cats_lines = "\n".join(
        f"{c.emoji} {c.name} — {c.percent}%"
        + (" ⚠️" if c.is_approximate else "")
        for c in result.categories
    )

    top = "\n".join(f"  • {c.emoji} {c.name} ({c.percent}%)" for c in result.top_categories)
    bottom = "\n".join(f"  • {c.emoji} {c.name} ({c.percent}%)" for c in result.bottom_categories)

    return (
        f"📊 <b>Результаты диагностики</b>\n\n"
        f"<b>Индекс зрелости:</b> {result.total_percent}%\n"
        f"<b>Уровень:</b> {result.maturity_level}\n"
        f"<b>Надёжность:</b> {result.reliability}\n\n"
        f"<b>Категории:</b>\n{cats_lines}\n\n"
        f"💪 <b>Сильные стороны:</b>\n{top}\n\n"
        f"📈 <b>Зоны роста:</b>\n{bottom}"
    )


def format_results_full(result: AssessmentResult, llm_sections: dict[str, str]) -> str:
    """Format full results with LLM analysis (Layer 1 + Layer 2)."""
    brief = format_results_brief(result)

    llm_text = ""
    if llm_sections.get("summary"):
        llm_text += f"\n\n🔎 <b>Интерпретация</b>\n{llm_sections['summary']}"
    if llm_sections.get("swot"):
        llm_text += f"\n\n📋 <b>SWOT-анализ</b>\n{llm_sections['swot']}"
    if llm_sections.get("recommendations"):
        llm_text += f"\n\n✅ <b>Рекомендации</b>\n{llm_sections['recommendations']}"
    if llm_sections.get("roadmap"):
        llm_text += f"\n\n🗺 <b>Roadmap</b>\n{llm_sections['roadmap']}"

    full = brief + llm_text

    # Telegram message limit — send truncated if too long
    if len(full) > 4000:
        return brief + "\n\n<i>Полный анализ доступен в PDF-отчёте.</i>"
    return full


def format_category_details(result: AssessmentResult) -> str:
    """Detailed per-category breakdown."""
    lines = []
    for c in result.categories:
        status = "⚠️ ориентировочно" if c.is_approximate else ""
        lines.append(
            f"{c.emoji} <b>{c.name}</b>\n"
            f"  Средний балл: {c.avg:.1f} / 5.0\n"
            f"  Процент: {c.percent}%\n"
            f"  Ответов: {c.valid_count}/5, пропусков: {c.unknown_count}\n"
            f"  {status}"
        )
    return "\n\n".join(lines)
