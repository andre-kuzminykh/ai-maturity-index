"""Seed database with categories, questions, and options."""
from app.db.questions_data import CATEGORIES_DATA


async def seed_database(session):
    """Populate categories, questions and options if empty."""
    from sqlalchemy import select
    from app.db.models import Category, Question, Option

    result = await session.execute(select(Category).limit(1))
    if result.scalars().first() is not None:
        return  # Already seeded

    for cat_data in CATEGORIES_DATA:
        category = Category(
            code=cat_data["code"],
            name=cat_data["name"],
            emoji=cat_data["emoji"],
            weight=cat_data["weight"],
            order=cat_data["order"],
        )
        session.add(category)
        await session.flush()

        for q_data in cat_data["questions"]:
            question = Question(
                category_id=category.id,
                code=q_data["code"],
                text=q_data["text"],
                short_explanation=q_data["short_explanation"],
                order=q_data["order"],
                is_active=True,
            )
            session.add(question)
            await session.flush()

            for opt_data in q_data["options"]:
                option = Option(
                    question_id=question.id,
                    score=opt_data["score"],
                    label_short=opt_data["label_short"],
                    text_full=opt_data["text_full"],
                    order=opt_data["score"],
                )
                session.add(option)

    await session.commit()
