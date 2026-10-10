"""
Chat Q&A: turn natural-language questions into structured DB queries via LLM.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.src.models.db_models import Category, Transaction

QUERY_SPEC_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": [
            "total_spend", "category_breakdown", "merchant_list",
            "trend", "top_merchants", "savings", "budget_status", "custom_filter"
        ]},
        "period": {"type": "string"},        # YYYY-MM or YYYY
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
        "category": {"type": "string"},
        "limit": {"type": "integer"},
        "direction": {"type": "string"},
    },
    "required": ["intent"],
}


def ask(session: Session, question: str) -> dict:
    """
    1. LLM parses question → query spec.
    2. Backend runs validated query.
    3. LLM narrates aggregated result.
    """
    # Step 1: parse intent
    system_parse = (
        "You are a personal finance assistant. "
        "Given a user question, extract a structured query spec as JSON. "
        "Period format: YYYY-MM. Return ONLY JSON."
    )
    categories = [c.name for c in session.query(Category).all()]

    try:
        from app.src.language_models.llm.gateway import get_gateway
        gateway = get_gateway()
        spec = gateway.run(system_parse, f"Categories: {categories}\nQuestion: {question}", QUERY_SPEC_SCHEMA)
    except Exception as e:
        logger.warning(f"Chat spec parse failed: {e}")
        return {"question": question, "answer": "Sorry, I couldn't understand that question.", "data": None}

    # Step 2: execute query
    data = _execute_spec(session, spec)

    # Step 3: narrate
    system_narrate = (
        "You are a friendly personal finance assistant. "
        "Given aggregated data, write a concise 1-3 sentence plain-language answer. "
        "Use ₹ for amounts. Return ONLY the answer text (not JSON)."
    )
    try:
        result = gateway.run(
            system_narrate,
            f"Question: {question}\nData: {data}",
            {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]},
        )
        answer = result.get("answer", str(data))
    except Exception:
        answer = f"Here's what I found: {data}"

    # Determine chart type
    chart_type = _suggest_chart(spec)
    return {
        "question": question,
        "answer": answer,
        "data": data,
        "chart_type": chart_type,
    }


def _execute_spec(session: Session, spec: dict) -> Any:
    intent = spec.get("intent", "total_spend")
    period = spec.get("period")
    start_date = spec.get("start_date", f"{period}-01" if period else None)
    end_date = spec.get("end_date")
    limit = spec.get("limit", 10)

    if end_date is None and period:
        import calendar
        if len(period) == 7:
            year, month = map(int, period.split("-"))
            last_day = calendar.monthrange(year, month)[1]
            end_date = f"{period}-{last_day:02d}"
        elif len(period) == 4:
            end_date = f"{period}-12-31"
            start_date = f"{period}-01-01"

    q = session.query(Transaction).filter(Transaction.direction == "debit", Transaction.status != "pending")
    if start_date:
        q = q.filter(Transaction.txn_date >= start_date)
    if end_date:
        q = q.filter(Transaction.txn_date <= end_date)

    cat_name = spec.get("category")
    if cat_name:
        cat = session.query(Category).filter(Category.name.ilike(cat_name)).first()
        if cat:
            q = q.filter(Transaction.category_id == cat.id)

    if intent == "total_spend":
        total = session.query(func.sum(Transaction.amount)).filter(
            *q.whereclause_parts() if hasattr(q, 'whereclause_parts') else []
        ).scalar()
        # Simpler approach:
        txns = q.all()
        total = sum(t.amount for t in txns)
        return {"total": str(total), "txn_count": len(txns)}

    elif intent == "category_breakdown":
        txns = q.all()
        breakdown: dict[str, float] = {}
        for t in txns:
            cat = session.get(Category, t.category_id) if t.category_id else None
            name = cat.name if cat else "Uncategorised"
            breakdown[name] = breakdown.get(name, 0.0) + float(t.amount)
        return sorted(breakdown.items(), key=lambda x: -x[1])

    elif intent == "top_merchants":
        from app.src.services.insights import top_merchants as _top
        return _top(session, period or "", limit)

    elif intent == "trend":
        txns = q.all()
        trend: dict[str, float] = {}
        for t in txns:
            month = t.txn_date[:7]
            trend[month] = trend.get(month, 0.0) + float(t.amount)
        return sorted(trend.items())

    elif intent == "savings":
        from app.src.services.insights import savings_rate
        return {"savings_rate": savings_rate(session, period)}

    else:
        txns = q.limit(limit).all()
        return [{"date": t.txn_date, "amount": str(t.amount), "narration": t.raw_narration} for t in txns]


def _suggest_chart(spec: dict) -> str | None:
    intent = spec.get("intent", "")
    if intent == "category_breakdown":
        return "donut"
    elif intent == "trend":
        return "line"
    elif intent == "top_merchants":
        return "bar"
    return None
