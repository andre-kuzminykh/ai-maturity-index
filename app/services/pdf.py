"""PDF report generation using WeasyPrint."""
from __future__ import annotations

import io
import logging
from jinja2 import Template

from app.services.scoring import AssessmentResult

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<style>
  body { font-family: sans-serif; margin: 40px; color: #333; font-size: 14px; }
  h1 { color: #1a1a2e; font-size: 24px; }
  h2 { color: #16213e; font-size: 18px; border-bottom: 2px solid #0f3460; padding-bottom: 4px; }
  .score-big { font-size: 48px; font-weight: bold; color: #0f3460; }
  .level { font-size: 20px; color: #e94560; }
  .reliability { font-size: 14px; color: #666; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #ddd; }
  th { background: #f5f5f5; }
  .bar-container { width: 200px; background: #eee; border-radius: 4px; }
  .bar { height: 18px; background: #0f3460; border-radius: 4px; }
  .section { margin: 20px 0; }
  .footer { margin-top: 40px; font-size: 12px; color: #999; border-top: 1px solid #ddd; padding-top: 10px; }
</style>
</head>
<body>
<h1>🤖 Отчёт: Диагностика ИИ-зрелости</h1>

<div class="section">
  <div class="score-big">{{ result.total_percent }}%</div>
  <div class="level">Уровень: {{ result.maturity_level }}</div>
  <div class="reliability">Надёжность: {{ result.reliability }}</div>
  {% if user_role %}<div>Роль: {{ user_role }}</div>{% endif %}
</div>

<h2>Результаты по категориям</h2>
<table>
  <tr><th>Категория</th><th>Результат</th><th></th></tr>
  {% for c in result.categories %}
  <tr>
    <td>{{ c.emoji }} {{ c.name }}</td>
    <td>{{ c.percent }}%</td>
    <td><div class="bar-container"><div class="bar" style="width: {{ c.percent }}%"></div></div></td>
  </tr>
  {% endfor %}
</table>

{% if llm_sections.summary %}
<h2>Интерпретация</h2>
<div class="section">{{ llm_sections.summary }}</div>
{% endif %}

{% if llm_sections.swot %}
<h2>SWOT-анализ</h2>
<div class="section">{{ llm_sections.swot | replace('\n', '<br>') }}</div>
{% endif %}

{% if llm_sections.recommendations %}
<h2>Рекомендации</h2>
<div class="section">{{ llm_sections.recommendations | replace('\n', '<br>') }}</div>
{% endif %}

{% if llm_sections.roadmap %}
<h2>Roadmap</h2>
<div class="section">{{ llm_sections.roadmap | replace('\n', '<br>') }}</div>
{% endif %}

<div class="footer">
  Сгенерировано ботом «Диагностика ИИ-зрелости»
</div>
</body>
</html>
"""


def generate_pdf(
    result: AssessmentResult,
    llm_sections: dict[str, str] | None = None,
    user_role: str | None = None,
) -> bytes:
    """Generate PDF report and return bytes."""
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError:
        logger.error("weasyprint not installed")
        raise RuntimeError("PDF generation unavailable: weasyprint not installed")

    template = Template(HTML_TEMPLATE)
    html_str = template.render(
        result=result,
        llm_sections=llm_sections or {},
        user_role=user_role,
    )

    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes
