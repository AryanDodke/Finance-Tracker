"""Review router: list open items and resolve them."""
import json

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from starlette.status import HTTP_404_NOT_FOUND

from app.src.dao.db import SessionDep
from app.src.dto.schemas import (
    BulkResolveIn,
    ResolveAnswer,
    ResolveResult,
    ReviewGroup,
    ReviewItemOut,
    ReviewOption,
)
from app.src.models.db_models import Category, ReviewItem, Transaction
from app.src.services.review_queue import counts, list_open, resolve, resolve_bulk

router = APIRouter()


def _item_to_schema(item: ReviewItem, session: Session) -> ReviewItemOut:
    options_raw = json.loads(item.options_json or "[]")
    options = [ReviewOption(label=o["label"], value=o["value"]) for o in options_raw]

    txn_out = None
    if item.txn_id:
        from app.api.routers.transactions import _enrich
        from app.src.dto.schemas import TxnOut
        txn = session.get(Transaction, item.txn_id)
        if txn:
            txn_out = TxnOut(**_enrich(txn, session))

    return ReviewItemOut(
        id=item.id,
        kind=item.kind,
        txn_id=item.txn_id,
        note_line_id=item.note_line_id,
        question=item.question,
        options=options,
        status=item.status,
        txn=txn_out,
    )


@router.get("", response_model=list[ReviewGroup])
def get_review(session: SessionDep):
    """Get open review items grouped by payee (unknown_payee first)."""
    groups = list_open(session)
    result = []
    for g in groups:
        items = [_item_to_schema(item, session) for item in g["items"]]
        result.append(ReviewGroup(
            payee=g["payee"],
            count=g["count"],
            items=items,
        ))
    return result


@router.get("/counts")
def get_counts(session: SessionDep):
    """Count open review items by kind."""
    return counts(session)


@router.post("/{item_id}/resolve", response_model=ResolveResult)
def resolve_item(
    item_id: int,
    body: ResolveAnswer,
    session: SessionDep,
    apply_scope: str = "this_only",
):
    """Resolve a review item with a category answer."""
    item = session.get(ReviewItem, item_id)
    if not item:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Review item not found.")

    result = resolve(session, item_id, body.category_id, apply_scope, skip=body.skip)
    return ResolveResult(
        resolved=result.resolved,
        rules_created=result.rules_created,
        txns_updated=result.txns_updated,
    )


@router.post("/bulk-resolve", response_model=ResolveResult)
def bulk_resolve(body: BulkResolveIn, session: SessionDep):
    """Resolve multiple review items at once."""
    result = resolve_bulk(session, body.item_ids, body.answer.category_id, body.apply_scope)
    return ResolveResult(
        resolved=result.resolved,
        rules_created=result.rules_created,
        txns_updated=result.txns_updated,
    )


@router.get("/categories")
def get_categories(session: SessionDep):
    """Return all categories for the review UI."""
    cats = session.query(Category).all()
    return [{"id": c.id, "name": c.name, "parent_id": c.parent_id} for c in cats]
