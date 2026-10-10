"""Reconcile router."""
from fastapi import APIRouter

from app.src.dao.db import SessionDep
from app.src.dto.schemas import (
    ReconcileCategoryGap,
    ReconcileLineMatch,
    ReconcileReport,
    TxnOut,
)
from app.src.services.reconciler import reconcile_period

router = APIRouter()


def _txn_to_out(txn, session) -> TxnOut:
    from app.api.routers.transactions import _enrich
    return TxnOut(**_enrich(txn, session))


@router.get("/{period}")
def get_reconcile(period: str, session: SessionDep):
    """Run (or re-run) reconciliation for a period and return the report."""
    report = reconcile_period(session, period)

    matched = [
        ReconcileLineMatch(
            note_id=m.note_id, note_item=m.note_item, note_amount=m.note_amount,
            txn_id=m.txn_id, txn_date=m.txn_date, txn_amount=m.txn_amount,
            merchant_name=m.merchant_name, match_score=m.match_score,
        ) for m in report.matched
    ]
    unmatched_notes = [
        ReconcileLineMatch(
            note_id=m.note_id, note_item=m.note_item, note_amount=m.note_amount,
            txn_id=None, txn_date=None, txn_amount=None,
            merchant_name=None, match_score=m.match_score,
        ) for m in report.unmatched_notes
    ]
    unmatched_txns = [_txn_to_out(t, session) for t in report.unmatched_txns]
    gaps = [
        ReconcileCategoryGap(
            category_name=g.category_name, noted_total=g.noted_total,
            bank_total=g.bank_total, gap=g.gap, gap_pct=g.gap_pct,
        ) for g in report.category_gaps
    ]

    return ReconcileReport(
        period=report.period,
        matched=matched,
        unmatched_notes=unmatched_notes,
        unmatched_txns=unmatched_txns,
        category_gaps=gaps,
    )
