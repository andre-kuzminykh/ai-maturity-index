"""
SQLite database layer with aiosqlite.
Stores users, assessments, and answers.
"""

import json
import logging
import os
from datetime import datetime, timezone

import aiosqlite

from bot.config import settings

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        db_path = settings.db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        _db = await aiosqlite.connect(db_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _init_tables(_db)
    return _db


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


async def _init_tables(db: aiosqlite.Connection):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            company_name TEXT,
            position TEXT,
            company_size TEXT,
            industry TEXT,
            email TEXT,
            phone TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'in_progress',
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            current_question_index INTEGER NOT NULL DEFAULT 0,
            total_score_percent REAL,
            maturity_level TEXT,
            result_json TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            answered_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (assessment_id) REFERENCES assessments(id),
            UNIQUE(assessment_id, question_id)
        );

        CREATE INDEX IF NOT EXISTS idx_assessments_user ON assessments(user_id);
        CREATE INDEX IF NOT EXISTS idx_assessments_status ON assessments(status);
        CREATE INDEX IF NOT EXISTS idx_answers_assessment ON answers(assessment_id);
    """)
    await db.commit()


# ── User operations ──


async def get_or_create_user(
    telegram_user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict:
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,)
    )
    if row:
        return dict(row[0])
    await db.execute(
        "INSERT INTO users (telegram_user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
        (telegram_user_id, username, first_name, last_name),
    )
    await db.commit()
    row = await db.execute_fetchall(
        "SELECT * FROM users WHERE telegram_user_id = ?", (telegram_user_id,)
    )
    return dict(row[0])


# ── Assessment operations ──


async def get_active_assessment(user_id: int) -> dict | None:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM assessments WHERE user_id = ? AND status = 'in_progress' ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    return dict(rows[0]) if rows else None


async def create_assessment(user_id: int) -> dict:
    db = await get_db()
    await db.execute(
        "UPDATE assessments SET status = 'abandoned' WHERE user_id = ? AND status = 'in_progress'",
        (user_id,),
    )
    await db.execute(
        "INSERT INTO assessments (user_id, status, current_question_index) VALUES (?, 'in_progress', 0)",
        (user_id,),
    )
    await db.commit()
    rows = await db.execute_fetchall(
        "SELECT * FROM assessments WHERE user_id = ? AND status = 'in_progress' ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    return dict(rows[0])


async def complete_assessment(
    assessment_id: int,
    total_score_percent: float,
    maturity_level: str,
    result_json: dict,
):
    db = await get_db()
    await db.execute(
        """UPDATE assessments
           SET status = 'completed',
               completed_at = datetime('now'),
               total_score_percent = ?,
               maturity_level = ?,
               result_json = ?
           WHERE id = ?""",
        (total_score_percent, maturity_level, json.dumps(result_json, ensure_ascii=False), assessment_id),
    )
    await db.commit()


async def update_assessment_question_index(assessment_id: int, index: int):
    db = await get_db()
    await db.execute(
        "UPDATE assessments SET current_question_index = ? WHERE id = ?",
        (index, assessment_id),
    )
    await db.commit()


# ── Answer operations ──


async def save_answer(assessment_id: int, question_id: int, score: int):
    db = await get_db()
    await db.execute(
        """INSERT INTO answers (assessment_id, question_id, score)
           VALUES (?, ?, ?)
           ON CONFLICT(assessment_id, question_id) DO UPDATE SET score = ?, answered_at = datetime('now')""",
        (assessment_id, question_id, score, score),
    )
    await db.commit()


async def get_answers_for_assessment(assessment_id: int) -> list[dict]:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM answers WHERE assessment_id = ? ORDER BY question_id",
        (assessment_id,),
    )
    return [dict(r) for r in rows]


async def delete_answers_from(assessment_id: int, question_id: int):
    """Delete answers starting from a given question_id (used when going back)."""
    db = await get_db()
    await db.execute(
        "DELETE FROM answers WHERE assessment_id = ? AND question_id >= ?",
        (assessment_id, question_id),
    )
    await db.commit()


# ── Admin operations ──


async def get_all_completed_assessments() -> list[dict]:
    db = await get_db()
    rows = await db.execute_fetchall(
        """SELECT a.id as assessment_id, a.started_at, a.completed_at,
                  a.total_score_percent, a.maturity_level, a.result_json,
                  u.telegram_user_id, u.username, u.first_name, u.last_name,
                  u.company_name, u.position, u.industry
           FROM assessments a
           JOIN users u ON a.user_id = u.id
           WHERE a.status = 'completed'
           ORDER BY a.completed_at DESC"""
    )
    return [dict(r) for r in rows]


async def get_assessment_stats() -> dict:
    db = await get_db()
    total_starts = await db.execute_fetchall(
        "SELECT COUNT(*) as cnt FROM assessments"
    )
    total_completed = await db.execute_fetchall(
        "SELECT COUNT(*) as cnt FROM assessments WHERE status = 'completed'"
    )
    total_abandoned = await db.execute_fetchall(
        "SELECT COUNT(*) as cnt FROM assessments WHERE status = 'abandoned'"
    )
    total_in_progress = await db.execute_fetchall(
        "SELECT COUNT(*) as cnt FROM assessments WHERE status = 'in_progress'"
    )
    avg_score = await db.execute_fetchall(
        "SELECT AVG(total_score_percent) as avg_score FROM assessments WHERE status = 'completed'"
    )
    return {
        "total_starts": total_starts[0]["cnt"],
        "total_completed": total_completed[0]["cnt"],
        "total_abandoned": total_abandoned[0]["cnt"],
        "total_in_progress": total_in_progress[0]["cnt"],
        "avg_score": round(avg_score[0]["avg_score"], 1) if avg_score[0]["avg_score"] else 0,
    }


async def update_user_contact_info(
    telegram_user_id: int,
    company_name: str | None = None,
    position: str | None = None,
    company_size: str | None = None,
    industry: str | None = None,
    email: str | None = None,
    phone: str | None = None,
):
    db = await get_db()
    fields = []
    values = []
    if company_name is not None:
        fields.append("company_name = ?")
        values.append(company_name)
    if position is not None:
        fields.append("position = ?")
        values.append(position)
    if company_size is not None:
        fields.append("company_size = ?")
        values.append(company_size)
    if industry is not None:
        fields.append("industry = ?")
        values.append(industry)
    if email is not None:
        fields.append("email = ?")
        values.append(email)
    if phone is not None:
        fields.append("phone = ?")
        values.append(phone)
    if fields:
        values.append(telegram_user_id)
        await db.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE telegram_user_id = ?",
            tuple(values),
        )
        await db.commit()
