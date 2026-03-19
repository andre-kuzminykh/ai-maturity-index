"""Admin panel — FastAPI-based."""
from __future__ import annotations

import csv
import io
import secrets
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.engine import async_session
from app.db.models import User, Assessment, Answer, Category, Question, Option

app = FastAPI(title="AI Maturity Admin", docs_url="/docs")
security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, settings.admin_username)
    correct_pass = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (correct_user and correct_pass):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.username


@app.get("/api/stats")
async def get_stats(admin: str = Depends(verify_credentials)):
    """Dashboard statistics."""
    async with async_session() as session:
        total_started = await session.scalar(select(func.count(Assessment.id)))
        total_completed = await session.scalar(
            select(func.count(Assessment.id)).where(Assessment.status == "completed")
        )
        total_users = await session.scalar(select(func.count(User.id)))

        # Average score
        avg_score = await session.scalar(
            select(func.avg(Assessment.total_score_percent))
            .where(Assessment.status == "completed")
        )

        # Level distribution
        levels = await session.execute(
            select(Assessment.maturity_level, func.count(Assessment.id))
            .where(Assessment.status == "completed")
            .group_by(Assessment.maturity_level)
        )
        level_dist = {row[0]: row[1] for row in levels}

    return {
        "total_users": total_users,
        "total_started": total_started,
        "total_completed": total_completed,
        "completion_rate": round(total_completed / total_started * 100, 1) if total_started else 0,
        "avg_score": round(avg_score, 1) if avg_score else None,
        "level_distribution": level_dist,
    }


@app.get("/api/assessments")
async def list_assessments(
    admin: str = Depends(verify_credentials),
    status: str | None = None,
    role: str | None = None,
    maturity_level: str | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
):
    """List assessments with filters."""
    async with async_session() as session:
        query = (
            select(Assessment)
            .options(selectinload(Assessment.user))
            .order_by(Assessment.started_at.desc())
        )
        if status:
            query = query.where(Assessment.status == status)
        if maturity_level:
            query = query.where(Assessment.maturity_level == maturity_level)
        if role:
            query = query.join(User).where(User.role == role)

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        assessments = result.scalars().all()

    return [
        {
            "id": a.id,
            "user": {
                "id": a.user.id,
                "telegram_user_id": a.user.telegram_user_id,
                "username": a.user.username,
                "first_name": a.user.first_name,
                "role": a.user.role,
                "email": a.user.email,
                "phone": a.user.phone,
            } if a.user else None,
            "status": a.status,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "total_score_percent": a.total_score_percent,
            "maturity_level": a.maturity_level,
            "reliability_level": a.reliability_level,
            "result_json": a.result_json,
            "llm_summary": a.llm_summary,
            "llm_swot": a.llm_swot,
            "llm_recommendations": a.llm_recommendations,
            "llm_roadmap": a.llm_roadmap,
        }
        for a in assessments
    ]


@app.get("/api/assessments/{assessment_id}")
async def get_assessment(assessment_id: int, admin: str = Depends(verify_credentials)):
    """Get single assessment with all answers."""
    async with async_session() as session:
        assessment = await session.get(Assessment, assessment_id)
        if not assessment:
            raise HTTPException(404, "Not found")

        user = await session.get(User, assessment.user_id)

        answers_result = await session.execute(
            select(Answer)
            .options(selectinload(Answer.question), selectinload(Answer.option))
            .where(Answer.assessment_id == assessment_id)
            .order_by(Answer.id)
        )
        answers = answers_result.scalars().all()

    return {
        "assessment": {
            "id": assessment.id,
            "status": assessment.status,
            "total_score_percent": assessment.total_score_percent,
            "maturity_level": assessment.maturity_level,
            "reliability_level": assessment.reliability_level,
            "result_json": assessment.result_json,
            "llm_summary": assessment.llm_summary,
            "llm_swot": assessment.llm_swot,
            "llm_recommendations": assessment.llm_recommendations,
            "llm_roadmap": assessment.llm_roadmap,
        },
        "user": {
            "username": user.username if user else None,
            "first_name": user.first_name if user else None,
            "role": user.role if user else None,
        },
        "answers": [
            {
                "question": ans.question.text if ans.question else None,
                "answer": ans.option.text_full if ans.option else "Не знаю",
                "score": ans.score,
                "is_unknown": ans.is_unknown,
            }
            for ans in answers
        ],
    }


@app.get("/api/export/csv")
async def export_csv(admin: str = Depends(verify_credentials)):
    """Export completed assessments as CSV."""
    async with async_session() as session:
        result = await session.execute(
            select(Assessment)
            .options(selectinload(Assessment.user))
            .where(Assessment.status == "completed")
            .order_by(Assessment.completed_at.desc())
        )
        assessments = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "User", "Role", "Score %", "Level", "Reliability",
        "Started", "Completed",
    ])
    for a in assessments:
        writer.writerow([
            a.id,
            a.user.username or a.user.first_name if a.user else "",
            a.user.role if a.user else "",
            a.total_score_percent,
            a.maturity_level,
            a.reliability_level,
            a.started_at.isoformat() if a.started_at else "",
            a.completed_at.isoformat() if a.completed_at else "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=assessments.csv"},
    )


@app.get("/api/questions")
async def list_questions(admin: str = Depends(verify_credentials)):
    """List all questions with options (for editing)."""
    async with async_session() as session:
        result = await session.execute(
            select(Question)
            .options(selectinload(Question.category), selectinload(Question.options))
            .order_by(Question.order)
        )
        questions = result.scalars().all()

    return [
        {
            "id": q.id,
            "code": q.code,
            "order": q.order,
            "category": q.category.name if q.category else None,
            "text": q.text,
            "short_explanation": q.short_explanation,
            "is_active": q.is_active,
            "options": [
                {"id": o.id, "score": o.score, "label_short": o.label_short, "text_full": o.text_full}
                for o in sorted(q.options, key=lambda x: x.order)
            ],
        }
        for q in questions
    ]


@app.put("/api/questions/{question_id}")
async def update_question(
    question_id: int,
    data: dict,
    admin: str = Depends(verify_credentials),
):
    """Update question text/explanation."""
    async with async_session() as session:
        question = await session.get(Question, question_id)
        if not question:
            raise HTTPException(404, "Not found")
        if "text" in data:
            question.text = data["text"]
        if "short_explanation" in data:
            question.short_explanation = data["short_explanation"]
        if "is_active" in data:
            question.is_active = data["is_active"]
        await session.commit()
    return {"ok": True}


@app.put("/api/options/{option_id}")
async def update_option(
    option_id: int,
    data: dict,
    admin: str = Depends(verify_credentials),
):
    """Update option label/text."""
    async with async_session() as session:
        option = await session.get(Option, option_id)
        if not option:
            raise HTTPException(404, "Not found")
        if "label_short" in data:
            option.label_short = data["label_short"]
        if "text_full" in data:
            option.text_full = data["text_full"]
        await session.commit()
    return {"ok": True}
