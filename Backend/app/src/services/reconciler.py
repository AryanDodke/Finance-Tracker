"""
Reconciler: two-pass matching of note lines against bank transactions per month.
Pass 1 - Item match (greedy one-to-one).
Pass 2 - Category totals gap report.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.setting import settings
from app.src.models.db_models import (
    Category,
    Merchant,
    NoteLine,
    Transaction,
)


@dataclass
class LineMatch:
    note_id: int
    note_item: str
    note_amount: Decimal
    txn_id: int | None
    txn_date: str | None
    txn_amount: Decimal | None
    merchant_name: str | None
    match_score: float


@dataclass
class CategoryGap:
    category_name: str
    noted_total: Decimal
    bank_total: Decimal
    gap: Decimal
    gap_pct: float


@dataclass
class ReconcileReport:
    period: str
    matched: list[LineMatch]
    unmatched_notes: list[LineMatch]
    unmatched_txns: list[Transaction]
    category_gaps: list[CategoryGap]


def _amount_match_score(note_amt: Decimal, txn_amt: Decimal) -> float:
    """1.0 for exact, partial for ≤2% difference, 0 otherwise."""
    if note_amt == txn_amt:
        return 1.0
    if note_amt == 0:
        return 0.0
    diff_pct = abs(note_amt - txn_amt) / note_amt
    if diff_pct <= 0.02:
        return 0.8
    return 0.0


def _text_similarity(a: str, b: str) -> float:
    """Simple token overlap similarity."""
    if not a or not b:
        return 0.0
    try:
        from rapidfuzz import fuzz
        return fuzz.token_sort_ratio(a.lower(), b.lower()) / 100.0
    except ImportError:
        # Fallback: word overlap
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return 0.0
        return len(a_words & b_words) / max(len(a_words), len(b_words))


def _score(note: NoteLine, txn: Transaction, session: Session) -> float:
    """
    score = 0.6 * amount_match + 0.3 * text_similarity + 0.1 * category_agreement
    """
    amount_score = _amount_match_score(note.amount, txn.amount)
    if amount_score == 0:
        return 0.0

    merchant_name = ""
    if txn.merchant_id:
        m = session.get(Merchant, txn.merchant_id)
        if m:
            merchant_name = m.canonical_name

    text_score = _text_similarity(note.item_text, merchant_name or txn.payee_raw or "")

    cat_score = 0.0
    if note.category_id and txn.category_id and note.category_id == txn.category_id:
        cat_score = 1.0

    return 0.6 * amount_score + 0.3 * text_score + 0.1 * cat_score


def reconcile_period(session: Session, period: str) -> ReconcileReport:
    """
    Run two-pass reconciliation for a given YYYY-MM period.
    """
    threshold = settings.reconcile_match_threshold
    gap_pct_threshold = settings.reconcile_gap_threshold_pct
    gap_abs_threshold = Decimal(str(settings.reconcile_gap_threshold_abs))

    # Fetch note lines for this period
    note_lines = session.query(NoteLine).filter_by(period=period).all()

    # Fetch bank debits for this period
    start = f"{period}-01"
    # End: last day of month
    year, month = map(int, period.split("-"))
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    end = f"{period}-{last_day:02d}"

    bank_txns = (
        session.query(Transaction)
        .filter(
            Transaction.txn_date >= start,
            Transaction.txn_date <= end,
            Transaction.direction == "debit",
            Transaction.status != "pending",
        )
        .all()
    )

    # ─── Pass 1: Item match ───────────────────────────────────────────────────

    matched: list[LineMatch] = []
    unmatched_notes: list[LineMatch] = []
    matched_txn_ids: set[int] = set()

    for note in note_lines:
        best_score = 0.0
        best_txn: Transaction | None = None

        for txn in bank_txns:
            if txn.id in matched_txn_ids:
                continue
            s = _score(note, txn, session)
            if s > best_score:
                best_score = s
                best_txn = txn

        if best_txn and best_score >= threshold:
            merchant_name = None
            if best_txn.merchant_id:
                m = session.get(Merchant, best_txn.merchant_id)
                if m:
                    merchant_name = m.canonical_name

            lm = LineMatch(
                note_id=note.id,
                note_item=note.item_text,
                note_amount=note.amount,
                txn_id=best_txn.id,
                txn_date=best_txn.txn_date,
                txn_amount=best_txn.amount,
                merchant_name=merchant_name,
                match_score=best_score,
            )
            matched.append(lm)
            matched_txn_ids.add(best_txn.id)

            # Update note line
            note.matched_txn_id = best_txn.id
            note.match_score = Decimal(str(best_score))
        else:
            unmatched_notes.append(LineMatch(
                note_id=note.id,
                note_item=note.item_text,
                note_amount=note.amount,
                txn_id=None, txn_date=None, txn_amount=None,
                merchant_name=None, match_score=best_score,
            ))

    unmatched_txns = [t for t in bank_txns if t.id not in matched_txn_ids]

    # ─── Pass 2: Category total gaps ─────────────────────────────────────────

    # Note totals per category
    note_by_cat: dict[int, Decimal] = {}
    for note in note_lines:
        if note.category_id:
            note_by_cat[note.category_id] = note_by_cat.get(note.category_id, Decimal("0")) + note.amount

    # Bank totals per category
    bank_by_cat: dict[int, Decimal] = {}
    for txn in bank_txns:
        if txn.category_id:
            bank_by_cat[txn.category_id] = bank_by_cat.get(txn.category_id, Decimal("0")) + txn.amount

    all_cat_ids = set(note_by_cat.keys()) | set(bank_by_cat.keys())
    category_gaps: list[CategoryGap] = []

    for cat_id in all_cat_ids:
        noted = note_by_cat.get(cat_id, Decimal("0"))
        bank = bank_by_cat.get(cat_id, Decimal("0"))
        gap = bank - noted
        gap_pct = float(abs(gap) / bank) if bank else 0.0

        if abs(gap) >= gap_abs_threshold or gap_pct >= gap_pct_threshold:
            cat = session.get(Category, cat_id)
            cat_name = cat.name if cat else f"cat_{cat_id}"
            category_gaps.append(CategoryGap(
                category_name=cat_name,
                noted_total=noted,
                bank_total=bank,
                gap=gap,
                gap_pct=gap_pct,
            ))

            # Create review items for significant gaps
            from app.src.services.review_queue import create_review_item
            create_review_item(
                session, "amount_gap",
                question=f"{cat_name}: notes show ₹{noted}, bank shows ₹{bank} (gap ₹{gap:+})",
                options=[
                    {"label": "Mark as explained", "value": "explain"},
                    {"label": "Fix categorisation", "value": "fix"},
                ],
            )

    # Create unmatched review items
    for unm in unmatched_notes:
        from app.src.services.review_queue import create_review_item
        create_review_item(
            session, "unmatched_note",
            note_line_id=unm.note_id,
            question=f"Note '{unm.note_item}' (₹{unm.note_amount}) has no matching bank transaction.",
            options=[
                {"label": "It's cash / not in bank", "value": "cash"},
                {"label": "Ignore", "value": "ignore"},
            ],
        )

    session.commit()

    return ReconcileReport(
        period=period,
        matched=matched,
        unmatched_notes=unmatched_notes,
        unmatched_txns=unmatched_txns,
        category_gaps=category_gaps,
    )
