# AI Maturity Index — Telegram Bot

Telegram-бот для диагностики ИИ-зрелости компании. 35 вопросов, 7 категорий, детерминированный расчёт без LLM.

## Быстрый старт

1. Создайте бота через [@BotFather](https://t.me/BotFather) и получите токен.

2. Скопируйте `.env.example` в `.env` и заполните:
   ```
   cp .env.example .env
   ```
   Укажите `BOT_TOKEN` и `ADMIN_IDS` (через запятую).

3. Запустите через Docker:
   ```
   docker compose up -d
   ```

   Или локально:
   ```
   pip install -r requirements.txt
   python main.py
   ```

## Команды бота

- `/start` — начать или продолжить диагностику
- `/stats` — статистика прохождений (только для админов)
- `/export` — выгрузка результатов в CSV (только для админов)

## Структура

```
bot/
  config.py       — настройки из .env
  database.py     — SQLite через aiosqlite
  handlers.py     — Telegram-хендлеры (aiogram 3)
  questions.py    — банк из 35 вопросов
  scoring.py      — логика подсчёта и рекомендации
  texts.py        — все тексты бота
main.py           — точка входа
```

## Логика подсчёта

- Каждый ответ: 1–5 баллов
- Балл категории: среднее 5 ответов, нормализация в 0–100%
- Общий индекс: взвешенное среднее по категориям
- Уровни: Начальный (0–20%), AI-Enabled (21–40%), AI-Driven (41–60%), AI-First (61–80%), AI-Native (81–100%)
