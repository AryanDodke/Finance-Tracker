"""Transactions router: list and patch."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND

from app.src.dao.db import SessionDep
from app.src.dto.schemas import TxnOut, TxnPatch
from app.src.models.db_models import Category, Merchant, Transaction

router = APIRouter()


def _enrich(txn: Transaction, session: Session) -> dict:
    merchant = session.get(Merchant, txn.merchant_id) if txn.merchant_id else None
    category = session.get(Category, txn.category_id) if txn.category_id else None
    return {
        "id": txn.id,
        "txn_hash": txn.txn_hash,
        "txn_date": txn.txn_date,
        "amount": txn.amount,
        "direction": txn.direction,
        "raw_narration": txn.raw_narration,
        "payee_raw": txn.payee_raw,
        "upi_ref": txn.upi_ref,
        "upi_handle": txn.upi_handle,
        "merchant_id": txn.merchant_id,
        "merchant_name": merchant.canonical_name if merchant else None,
        "category_id": txn.category_id,
        "category_name": category.name if category else None,
        "confidence": txn.confidence,
        "status": txn.status,
        "cat_source": txn.cat_source,
    }


@router.get("", response_model=list[TxnOut])
def get_transactions(
    session: SessionDep,
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    category_id: int | None = Query(None),
    merchant_id: int | None = Query(None),
    status: str | None = Query(None),
    direction: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List transactions with optional filters."""
    q = session.query(Transaction)

    if start_date:
        q = q.filter(Transaction.txn_date >= start_date)
    if end_date:
        q = q.filter(Transaction.txn_date <= end_date)
    if category_id is not None:
        q = q.filter(Transaction.category_id == category_id)
    if merchant_id is not None:
        q = q.filter(Transaction.merchant_id == merchant_id)
    if status:
        q = q.filter(Transaction.status == status)
    if direction:
        q = q.filter(Transaction.direction == direction)

    q = q.order_by(Transaction.txn_date.desc())
    offset = (page - 1) * page_size
    txns = q.offset(offset).limit(page_size).all()

    return [TxnOut(**_enrich(t, session)) for t in txns]


@router.patch("/{txn_id}", response_model=TxnOut)
def patch_transaction(
    txn_id: int,
    body: TxnPatch,
    session: SessionDep,
):
    """Re-categorise a transaction with optional rule creation."""
    txn = session.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Transaction not found.")

    cat = session.get(Category, body.category_id)
    if not cat:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Category not found.")

    from decimal import Decimal
    txn.category_id = body.category_id
    txn.confidence = Decimal("1.0")
    txn.status = "confirmed"
    txn.cat_source = "user"

    if body.create_rule or body.apply_scope == "all_past_and_future":
        from app.src.services.categoriser import apply_rule_retroactively, create_rule
        rule = create_rule(
            session,
            match_type="payee",
            pattern=txn.payee_raw or "",
            category_id=body.category_id,
            created_from="user",
            priority=20,
        )
        if body.apply_scope in ("all_past", "all_past_and_future"):
            apply_rule_retroactively(session, rule)

    elif body.apply_scope == "all_past":
        payee = txn.payee_raw or ""
        if payee:
            from decimal import Decimal
            similar = session.query(Transaction).filter(Transaction.payee_raw == payee).all()
            for t in similar:
                t.category_id = body.category_id
                t.confidence = Decimal("1.0")
                t.status = "confirmed"
                t.cat_source = "user"

    session.commit()
    return TxnOut(**_enrich(txn, session))
