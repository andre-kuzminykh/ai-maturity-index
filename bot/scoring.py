"""
Deterministic scoring logic for AI Maturity Index.
No LLM, no generation — pure arithmetic + static templates.
"""

from bot.questions import CATEGORIES, CATEGORY_BY_CODE, QUESTIONS, QUESTION_BY_ID


def calculate_results(answers: list[dict]) -> dict:
    """
    Calculate full assessment results from a list of answers.
    Each answer: {"question_id": int, "score": int}
    Returns a dict with all results for display and storage.
    """
    # Group scores by category
    category_scores: dict[str, list[int]] = {c.code: [] for c in CATEGORIES}
    for ans in answers:
        q = QUESTION_BY_ID[ans["question_id"]]
        category_scores[q.category_code].append(ans["score"])

    # Calculate per-category averages
    category_avgs: dict[str, float] = {}
    category_percents: dict[str, float] = {}
    for cat in CATEGORIES:
        scores = category_scores[cat.code]
        if scores:
            avg = sum(scores) / len(scores)
        else:
            avg = 1.0
        category_avgs[cat.code] = avg
        category_percents[cat.code] = round(((avg - 1) / 4) * 100, 1)

    # Weighted average
    weighted_avg = sum(
        category_avgs[cat.code] * cat.weight for cat in CATEGORIES
    )
    total_percent = round(((weighted_avg - 1) / 4) * 100, 1)

    # Maturity level
    level = _maturity_level(total_percent)

    # Strong and weak zones
    sorted_cats = sorted(CATEGORIES, key=lambda c: category_percents[c.code])
    weak_zones = [
        {"code": c.code, "name": c.name, "percent": category_percents[c.code]}
        for c in sorted_cats[:3]
    ]
    strong_zones = [
        {"code": c.code, "name": c.name, "percent": category_percents[c.code]}
        for c in sorted_cats[-3:]
    ][::-1]

    # Interpretation
    interpretation = _get_interpretation(total_percent, level)

    # Recommendations for 3 weakest categories
    recommendations = []
    for zone in weak_zones:
        rec = _get_recommendation(zone["code"], zone["percent"])
        recommendations.append({"category": zone["name"], "text": rec})

    return {
        "total_percent": total_percent,
        "weighted_avg": round(weighted_avg, 2),
        "maturity_level": level,
        "categories": {
            cat.code: {
                "name": cat.name,
                "avg": round(category_avgs[cat.code], 2),
                "percent": category_percents[cat.code],
            }
            for cat in CATEGORIES
        },
        "strong_zones": strong_zones,
        "weak_zones": weak_zones,
        "interpretation": interpretation,
        "recommendations": recommendations,
    }


def _maturity_level(percent: float) -> str:
    if percent <= 20:
        return "Начальный"
    elif percent <= 40:
        return "AI-Enabled"
    elif percent <= 60:
        return "AI-Driven"
    elif percent <= 80:
        return "AI-First"
    return "AI-Native"


def _get_interpretation(percent: float, level: str) -> str:
    if percent <= 20:
        return (
            f"Ваша компания находится на начальном уровне ИИ-зрелости. "
            f"ИИ пока не является частью стратегии и процессов. "
            f"Рекомендуется начать с формирования видения и пилотных проектов."
        )
    elif percent <= 40:
        return (
            f"Компания находится на уровне AI-Enabled. "
            f"Есть первые шаги и эксперименты, но системного подхода пока нет. "
            f"Главная задача — перейти от точечных инициатив к целостной стратегии."
        )
    elif percent <= 60:
        return (
            f"Компания находится на уровне AI-Driven. "
            f"У вас уже формируется системный подход к ИИ, однако ИИ пока не стал "
            f"операционным ядром бизнеса. Главная задача — перейти от локальных "
            f"внедрений к масштабируемой модели."
        )
    elif percent <= 80:
        return (
            f"Компания находится на уровне AI-First. "
            f"ИИ глубоко интегрирован в процессы и стратегию. "
            f"Следующий шаг — достижение полной автономности ИИ-контуров "
            f"и выход на уровень AI-Native."
        )
    return (
        f"Компания находится на уровне AI-Native. "
        f"ИИ является фундаментом бизнес-модели и операционной системой. "
        f"Фокус — на удержании лидерства, развитии R&D и формировании "
        f"отраслевых стандартов."
    )


# ── Static recommendation templates per category and level ──

RECOMMENDATIONS: dict[str, dict[str, str]] = {
    "strategy": {
        "low": (
            "У компании отсутствует системная ИИ-стратегия. "
            "Начните с формирования видения, назначения ответственных "
            "и определения первых приоритетных направлений."
        ),
        "mid": (
            "Стратегия в процессе формирования. Следующий шаг — "
            "связать ИИ-инициативы с бизнес-KPI и обеспечить "
            "регулярный контур управления на уровне руководства."
        ),
        "high": (
            "Стратегия зрелая. Рекомендуется углублять интеграцию ИИ "
            "в операционную модель и развивать метрики влияния ИИ на бизнес."
        ),
    },
    "people": {
        "low": (
            "Компании не хватает ИИ-талантов и культуры. "
            "Начните с программ обучения, определения ключевых ролей "
            "и формирования внутреннего сообщества практиков."
        ),
        "mid": (
            "Команды формируются, но культура ИИ ещё не устоялась. "
            "Следующий шаг — системное обучение по ролям и "
            "создание кросс-функциональных команд."
        ),
        "high": (
            "Сильная ИИ-культура. Развивайте внутреннюю академию, "
            "партнёрства с университетами и программу менторства."
        ),
    },
    "infrastructure": {
        "low": (
            "Инфраструктура не готова к ИИ-нагрузкам. "
            "Начните с создания централизованной среды разработки, "
            "базовых политик безопасности и облачных ресурсов."
        ),
        "mid": (
            "Базовая инфраструктура есть, но не хватает масштабируемости. "
            "Следующий шаг — единая ИИ-платформа с самообслуживанием "
            "и автоматизированным мониторингом."
        ),
        "high": (
            "Инфраструктура зрелая. Развивайте AIOps, предиктивный "
            "мониторинг и глобальную масштабируемость."
        ),
    },
    "data": {
        "low": (
            "У вас слабая готовность данных к ИИ. "
            "Начать стоит с инвентаризации источников, владельцев данных "
            "и построения базового Data Governance."
        ),
        "mid": (
            "Данные уже используются, но пока не образуют сквозной фабрики данных. "
            "Следующий шаг — централизовать ключевые потоки "
            "и автоматизировать контроль качества."
        ),
        "high": (
            "У вас сильная дата-основа для ИИ. Следующий шаг — "
            "плотнее связать фабрику данных с ИИ-пайплайнами "
            "и контуром переобучения."
        ),
    },
    "models": {
        "low": (
            "Портфель моделей минимален или отсутствует. "
            "Начните с каталогизации существующих моделей, "
            "стандартизации пайплайнов и внедрения базового MLOps."
        ),
        "mid": (
            "Модели есть, но процесс вывода в прод нестабилен. "
            "Следующий шаг — стандартизировать CI/CD для моделей, "
            "внедрить мониторинг дрифта и версионирование."
        ),
        "high": (
            "Зрелый портфель моделей. Развивайте автоматическое "
            "переобучение, A/B-тестирование и управление моделями "
            "как стратегическим активом."
        ),
    },
    "implementation": {
        "low": (
            "ИИ практически не внедрён в бизнес-процессы. "
            "Начните с пилотных внедрений в 2–3 ключевых функциях "
            "и измерения эффекта."
        ),
        "mid": (
            "ИИ внедрён точечно. Следующий шаг — масштабировать "
            "успешные кейсы, создать фреймворк внедрения "
            "и центр компетенций."
        ),
        "high": (
            "Высокий уровень внедрения. Развивайте AgentOps-контур, "
            "автономные ИИ-процессы и персонализацию клиентского пути."
        ),
    },
    "rnd": {
        "low": (
            "R&D-функция отсутствует. Начните с формирования "
            "исследовательского контура: гипотезы, эксперименты, "
            "партнёрства с университетами."
        ),
        "mid": (
            "Есть базовый R&D, но результаты не всегда доходят до продакшена. "
            "Следующий шаг — связать исследования с продуктовым контуром "
            "и выделить бюджет на НИОКР."
        ),
        "high": (
            "Сильный R&D. Развивайте публикационную активность, "
            "участие в стандартизации и стратегические научные альянсы."
        ),
    },
}


def _get_recommendation(category_code: str, percent: float) -> str:
    templates = RECOMMENDATIONS.get(category_code, {})
    if percent <= 40:
        return templates.get("low", "")
    elif percent <= 60:
        return templates.get("mid", "")
    return templates.get("high", "")
