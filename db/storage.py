"""Database operations for users, assessments and answers."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite


class Storage:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    # ── Users ─────────────────────────────────────────────────────

    async def get_or_create_user(self, tg_user) -> int:
        cur = await self.db.execute(
            "SELECT id FROM users WHERE telegram_user_id = ?",
            (tg_user.id,),
        )
        row = await cur.fetchone()
        if row:
            return row[0]
        cur = await self.db.execute(
            "INSERT INTO users (telegram_user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
            (tg_user.id, tg_user.username, tg_user.first_name, tg_user.last_name),
        )
        await self.db.commit()
        return cur.lastrowid

    # ── Assessments ───────────────────────────────────────────────

    async def get_active_assessment(self, user_id: int) -> dict | None:
        cur = await self.db.execute(
            "SELECT * FROM assessments WHERE user_id = ? AND status = 'in_progress' ORDER BY started_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cur.fetchone()
        if row:
            return dict(row)
        return None

    async def create_assessment(self, user_id: int) -> int:
        cur = await self.db.execute(
            "INSERT INTO assessments (user_id, status, current_question_index) VALUES (?, 'in_progress', 0)",
            (user_id,),
        )
        await self.db.commit()
        return cur.lastrowid

    async def update_assessment_progress(self, assessment_id: int, question_index: int):
        await self.db.execute(
            "UPDATE assessments SET current_question_index = ? WHERE id = ?",
            (question_index, assessment_id),
        )
        await self.db.commit()

    async def complete_assessment(self, assessment_id: int, result: dict):
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """UPDATE assessments
               SET status = 'completed',
                   completed_at = ?,
                   total_score_percent = ?,
                   maturity_level = ?,
                   reliability_level = ?,
                   result_json = ?
               WHERE id = ?""",
            (
                now,
                result["total_percent"],
                result["maturity_level"],
                result["reliability"],
                json.dumps(result, ensure_ascii=False),
                assessment_id,
            ),
        )
        await self.db.commit()

    async def save_llm_analysis(self, assessment_id: int, analysis: str):
        await self.db.execute(
            "UPDATE assessments SET llm_analysis = ? WHERE id = ?",
            (analysis, assessment_id),
        )
        await self.db.commit()

    async def abandon_assessment(self, assessment_id: int):
        await self.db.execute(
            "UPDATE assessments SET status = 'abandoned' WHERE id = ?",
            (assessment_id,),
        )
        await self.db.commit()

    async def get_last_completed(self, user_id: int) -> dict | None:
        cur = await self.db.execute(
            "SELECT * FROM assessments WHERE user_id = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    # ── Answers ───────────────────────────────────────────────────

    async def save_answer(
        self,
        assessment_id: int,
        question_code: str,
        category_code: str,
        option_value: int | None,
        score: int | None,
        is_unknown: bool,
    ):
        await self.db.execute(
            """INSERT INTO answers (assessment_id, question_code, category_code, option_value, score, is_unknown)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(assessment_id, question_code)
               DO UPDATE SET option_value = ?, score = ?, is_unknown = ?, answered_at = CURRENT_TIMESTAMP""",
            (
                assessment_id, question_code, category_code, option_value, score, int(is_unknown),
                option_value, score, int(is_unknown),
            ),
        )
        await self.db.commit()

    async def get_answers(self, assessment_id: int) -> list[dict]:
        cur = await self.db.execute(
            "SELECT * FROM answers WHERE assessment_id = ? ORDER BY id",
            (assessment_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def delete_answer(self, assessment_id: int, question_code: str):
        await self.db.execute(
            "DELETE FROM answers WHERE assessment_id = ? AND question_code = ?",
            (assessment_id, question_code),
        )
        await self.db.commit()

    async def delete_all_answers(self, assessment_id: int):
        await self.db.execute(
            "DELETE FROM answers WHERE assessment_id = ?",
            (assessment_id,),
        )
        await self.db.commit()
