"""
Insights engine: aggregations, trends, recurring detection, anomalies, budgets.
"""
from __future__ import annotations

from decimal import Decimal
from statistics import mean, stdev

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.src.models.db_models import Budget, Category, Merchant, Transaction

# ─── Monthly totals ──────────────────────────────────────────────────────────

def monthly_totals(session: Session, start: str, end: str) -> list[dict]:
    """Category totals per month between start/end YYYY-MM."""
    rows = (
        session.query(
            func.substr(Transaction.txn_date, 1, 7).label("period"),
            Transaction.category_id,
            func.sum(Transaction.amount).label("total"),
        )
        .filter(
            Transaction.txn_date >= f"{start}-01",
            Transaction.txn_date <= f"{end}-31",
            Transaction.direction == "debit",
            Transaction.status != "pending",
        )
        .group_by("period", Transaction.category_id)
        .all()
    )

    result = []
    for row in rows:
        cat = session.get(Category, row.category_id) if row.category_id else None
        if cat and cat.name == "Transfer":
            continue
        result.append({
            "period": row.period,
            "category_id": row.category_id,
            "category_name": cat.name if cat else "Uncategorised",
            "category_icon": cat.icon if cat else "face-unknown",
            "total": Decimal(str(row.total)),
        })
    return result


def mom_change(session: Session, period: str) -> list[dict]:
    """Month-over-month change for a given YYYY-MM."""
    year, month = map(int, period.split("-"))
    if month == 1:
        prev_period = f"{year-1}-12"
    else:
        prev_period = f"{year}-{month-1:02d}"

    current = monthly_totals(session, period, period)
    previous = monthly_totals(session, prev_period, prev_period)

    current_map = {r["category_id"]: r["total"] for r in current}
    previous_map = {r["category_id"]: r["total"] for r in previous}

    all_cats = set(current_map.keys()) | set(previous_map.keys())
    result = []
    for cat_id in all_cats:
        curr = current_map.get(cat_id, Decimal("0"))
        prev = previous_map.get(cat_id, Decimal("0"))
        pct = None
        if prev > 0:
            pct = float((curr - prev) / prev * 100)
        cat = session.get(Category, cat_id) if cat_id else None
        result.append({
            "category_id": cat_id,
            "category_name": cat.name if cat else "Uncategorised",
            "category_icon": cat.icon if cat else "face-unknown",
            "current": curr,
            "previous": prev,
            "change_pct": pct,
        })
    return result


def rolling_average(session: Session, category_id: int, months: int = 3) -> Decimal:
    """3-month rolling average for a category."""
    rows = (
        session.query(func.sum(Transaction.amount))
        .filter(
            Transaction.category_id == category_id,
            Transaction.direction == "debit",
            Transaction.status != "pending",
        )
        .group_by(func.substr(Transaction.txn_date, 1, 7))
        .order_by(func.substr(Transaction.txn_date, 1, 7).desc())
        .limit(months)
        .all()
    )
    totals = [Decimal(str(r[0])) for r in rows if r[0]]
    if not totals:
        return Decimal("0")
    return sum(totals) / Decimal(len(totals))


def top_merchants(session: Session, period: str, limit: int = 10) -> list[dict]:
    rows = (
        session.query(
            Transaction.merchant_id,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("txn_count"),
        )
        .filter(
            func.substr(Transaction.txn_date, 1, 7) == period,
            Transaction.direction == "debit",
            Transaction.status != "pending",
        )
        .group_by(Transaction.merchant_id)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
        .all()
    )
    result = []
    for row in rows:
        m = session.get(Merchant, row.merchant_id) if row.merchant_id else None
        result.append({
            "merchant_id": row.merchant_id or 0,
            "merchant_name": m.canonical_name if m else "Unknown",
            "total": Decimal(str(row.total)),
            "txn_count": row.txn_count,
        })
    return result


def detect_recurring(session: Session) -> list[dict]:
    """Detect recurring charges: same merchant, similar amount, 25-35 day cadence."""
    merchants = session.query(Merchant).all()
    result = []

    for merchant in merchants:
        txns = (
            session.query(Transaction)
            .filter(
                Transaction.merchant_id == merchant.id,
                Transaction.direction == "debit",
                Transaction.status != "pending",
            )
            .order_by(Transaction.txn_date)
            .all()
        )
        if len(txns) < 2:
            continue

        amounts = [float(t.amount) for t in txns]
        avg_amount = mean(amounts)

        # Check amount consistency (std < 10% of mean)
        if len(amounts) > 1 and stdev(amounts) > 0.1 * avg_amount:
            continue

        # Check date cadence
        from datetime import date
        dates = [date.fromisoformat(t.txn_date) for t in txns]
        gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        if not gaps:
            continue
        avg_gap = mean(gaps)

        if 25 <= avg_gap <= 35:
            result.append({
                "merchant_id": merchant.id,
                "merchant_name": merchant.canonical_name,
                "typical_amount": Decimal(str(avg_amount)),
                "last_date": txns[-1].txn_date,
                "frequency_days": round(avg_gap),
            })

    return result


def detect_anomalies(session: Session, period: str, z: float = 3.0) -> list[dict]:
    """Flag transactions > mean + z*std for their category in the given period."""
    year, month = period.split("-")
    start = f"{period}-01"
    import calendar
    last_day = calendar.monthrange(int(year), int(month))[1]
    end = f"{period}-{last_day:02d}"

    categories = session.query(Category).all()
    result = []

    for cat in categories:
        if cat.name in ("Transfer", "Income"):
            continue

        txns = (
            session.query(Transaction)
            .filter(
                Transaction.category_id == cat.id,
                Transaction.direction == "debit",
                Transaction.status != "pending",
            )
            .all()
        )
        if len(txns) < 3:
            continue

        amounts = [float(t.amount) for t in txns]
        mu = mean(amounts)
        sigma = stdev(amounts)
        if sigma == 0:
            continue

        period_txns = [t for t in txns if start <= t.txn_date <= end]
        for txn in period_txns:
            z_score = (float(txn.amount) - mu) / sigma
            if z_score > z:
                m = session.get(Merchant, txn.merchant_id) if txn.merchant_id else None
                result.append({
                    "txn_id": txn.id,
                    "txn_date": txn.txn_date,
                    "merchant_name": m.canonical_name if m else txn.payee_raw,
                    "amount": txn.amount,
                    "category_name": cat.name,
                    "category_icon": cat.icon,
                    "z_score": round(z_score, 2),
                })

    return result


def savings_rate(session: Session, period: str) -> float | None:
    """Savings rate = (income - total_spend) / income for a period."""
    start = f"{period}-01"
    import calendar
    year, month = map(int, period.split("-"))
    end = f"{period}-{calendar.monthrange(year, month)[1]:02d}"

    income_cat = session.query(Category).filter_by(name="Income").first()
    income = Decimal("0")
    if income_cat:
        r = session.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == income_cat.id,
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
            Transaction.direction == "credit",
        ).scalar()
        if r:
            income = Decimal(str(r))

    if income <= 0:
        return None

    spend = Decimal("0")
    r = session.query(func.sum(Transaction.amount)).filter(
        Transaction.direction == "debit",
        Transaction.txn_date >= start,
        Transaction.txn_date <= end,
        Transaction.status != "pending",
    ).scalar()
    if r:
        spend = Decimal(str(r))

    return float((income - spend) / income * 100)


def budget_vs_actual(session: Session, period: str) -> list[dict]:
    """Compare budgets vs actual spending for a period."""
    budgets = (
        session.query(Budget)
        .filter(Budget.effective_from <= period)
        .order_by(Budget.effective_from.desc())
        .all()
    )

    # Most recent budget per category
    seen_cats: set[int] = set()
    active_budgets: list[Budget] = []
    for b in budgets:
        if b.category_id not in seen_cats:
            active_budgets.append(b)
            seen_cats.add(b.category_id)

    result = []
    import calendar
    year, month = map(int, period.split("-"))
    start = f"{period}-01"
    end = f"{period}-{calendar.monthrange(year, month)[1]:02d}"

    for budget in active_budgets:
        actual_row = session.query(func.sum(Transaction.amount)).filter(
            Transaction.category_id == budget.category_id,
            Transaction.direction == "debit",
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
            Transaction.status != "pending",
        ).scalar()
        actual = Decimal(str(actual_row)) if actual_row else Decimal("0")
        remaining = budget.monthly_amount - actual
        pct = float(actual / budget.monthly_amount * 100) if budget.monthly_amount else 0.0

        cat = session.get(Category, budget.category_id)
        result.append({
            "category_id": budget.category_id,
            "category_name": cat.name if cat else "Unknown",
            "category_icon": cat.icon if cat else "face-unknown",
            "budget": budget.monthly_amount,
            "actual": actual,
            "remaining": remaining,
            "pct_used": pct,
        })
    return result


def build_summary(session: Session, period: str) -> dict:
    """Aggregate all insights for the dashboard."""
    from app.src.services.review_queue import counts as review_counts

    return {
        "period": period,
        "category_totals": monthly_totals(session, period, period),
        "mom_changes": mom_change(session, period),
        "top_merchants": top_merchants(session, period),
        "recurring": detect_recurring(session),
        "anomalies": detect_anomalies(session, period),
        "budget_status": budget_vs_actual(session, period),
        "savings_rate": savings_rate(session, period),
        "review_count": review_counts(session).get("total", 0),
    }
