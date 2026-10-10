"""Insights router."""
from fastapi import APIRouter, Query

from app.src.dao.db import SessionDep
from app.src.dto.schemas import BudgetIn, BudgetOut
from app.src.models.db_models import Budget, Category
from app.src.services.insights import build_summary

router = APIRouter()


@router.get("/summary")
def get_summary(
    session: SessionDep,
    period: str = Query(..., description="YYYY-MM"),
):
    """Full insights summary for the dashboard."""
    return build_summary(session, period)


@router.get("/budgets", response_model=list[BudgetOut])
def get_budgets(session: SessionDep):
    budgets = session.query(Budget).all()
    result = []
    for b in budgets:
        cat = session.get(Category, b.category_id)
        result.append(BudgetOut(
            id=b.id,
            category_id=b.category_id,
            category_name=cat.name if cat else None,
            monthly_amount=b.monthly_amount,
            effective_from=b.effective_from,
        ))
    return result


@router.put("/budgets", response_model=BudgetOut)
def upsert_budget(body: BudgetIn, session: SessionDep):
    """Create or update a budget for a category."""
    existing = session.query(Budget).filter_by(
        category_id=body.category_id,
        effective_from=body.effective_from,
    ).first()

    if existing:
        existing.monthly_amount = body.monthly_amount
        session.commit()
        b = existing
    else:
        b = Budget(
            category_id=body.category_id,
            monthly_amount=body.monthly_amount,
            effective_from=body.effective_from,
        )
        session.add(b)
        session.commit()

    cat = session.get(Category, b.category_id)
    return BudgetOut(
        id=b.id,
        category_id=b.category_id,
        category_name=cat.name if cat else None,
        monthly_amount=b.monthly_amount,
        effective_from=b.effective_from,
    )


@router.get("/categories")
def get_categories(session: SessionDep):
    cats = session.query(Category).all()
    return [{"id": c.id, "name": c.name, "parent_id": c.parent_id} for c in cats]
