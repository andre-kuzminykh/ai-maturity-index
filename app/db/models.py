import datetime
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.engine import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    assessments: Mapped[list["Assessment"]] = relationship(back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    emoji: Mapped[str] = mapped_column(String(10))
    weight: Mapped[float] = mapped_column(Float)
    order: Mapped[int] = mapped_column(Integer)

    questions: Mapped[list["Question"]] = relationship(back_populates="category", order_by="Question.order")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"))
    code: Mapped[str] = mapped_column(String(10), unique=True)
    text: Mapped[str] = mapped_column(Text)
    short_explanation: Mapped[str] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["Category"] = relationship(back_populates="questions")
    options: Mapped[list["Option"]] = relationship(back_populates="question", order_by="Option.order")


class Option(Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"))
    score: Mapped[int] = mapped_column(Integer)
    label_short: Mapped[str] = mapped_column(String(50))
    text_full: Mapped[str] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer)

    question: Mapped["Question"] = relationship(back_populates="options")


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_question_order: Mapped[int] = mapped_column(Integer, default=1)
    total_score_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    maturity_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reliability_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    llm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_swot: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_roadmap: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="assessments")
    answers: Mapped[list["Answer"]] = relationship(back_populates="assessment")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(Integer, ForeignKey("assessments.id"))
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"))
    option_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("options.id"), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_unknown: Mapped[bool] = mapped_column(Boolean, default=False)
    answered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship()
    option: Mapped["Option | None"] = relationship()
