"""
Review Queue service: creates, groups, and resolves review items.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.src.models.db_models import ReviewItem, Transaction


@dataclass
class ResolveResult:
    resolved: int
    rules_created: int
    txns_updated: int


def create_review_item(
    session: Session,
    kind: str,
    *,
    txn_id: int | None = None,
    note_line_id: int | None = None,
    question: str,
    options: list[dict],
) -> ReviewItem:
    """Create a review item, deduplicating by (kind, txn_id, note_line_id)."""
    # Dedupe: don't create duplicate items for the same transaction
    existing = session.query(ReviewItem).filter_by(
        kind=kind, txn_id=txn_id, note_line_id=note_line_id, status="open"
    ).first()
    if existing:
        return existing

    item = ReviewItem(
        kind=kind,
        txn_id=txn_id,
        note_line_id=note_line_id,
        question=question,
        options_json=json.dumps(options),
        status="open",
    )
    session.add(item)
    session.flush()
    return item


def list_open(session: Session, group_by: str = "payee") -> list[dict]:
    """Return open items grouped by payee/kind, unknown_payees first."""
    items = (
        session.query(ReviewItem)
        .filter_by(status="open")
        .order_by(ReviewItem.kind)
        .all()
    )

    groups: dict[str, list] = {}
    for item in items:
        # Group key
        key = _group_key(session, item)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)

    # Sort: unknown_payee groups first, then by size descending
    result = []
    for key, group_items in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
        first = group_items[0]
        result.append({
            "payee": key,
            "count": len(group_items),
            "kind": first.kind,
            "items": group_items,
        })
    return result


def _group_key(session: Session, item: ReviewItem) -> str:
    if item.txn_id:
        txn = session.get(Transaction, item.txn_id)
        if txn:
            return txn.payee_raw or txn.raw_narration[:40] or f"txn_{txn.id}"
    if item.note_line_id:
        return f"note_{item.note_line_id}"
    return f"item_{item.id}"


def resolve(
    session: Session,
    item_id: int,
    category_id: int | None,
    apply_scope: str,  # this_only | all_past | all_past_and_future
    skip: bool = False,
) -> ResolveResult:
    """Resolve a single review item."""
    item = session.get(ReviewItem, item_id)
    if not item:
        return ResolveResult(resolved=0, rules_created=0, txns_updated=0)

    if skip:
        item.status = "skipped"
        session.commit()
        return ResolveResult(resolved=1, rules_created=0, txns_updated=0)

    if not category_id:
        return ResolveResult(resolved=0, rules_created=0, txns_updated=0)

    from decimal import Decimal

    rules_created = 0
    txns_updated = 0

    # Resolve the item's transaction
    if item.txn_id:
        txn = session.get(Transaction, item.txn_id)
        if txn:
            txn.category_id = category_id
            txn.confidence = Decimal("1.0")
            txn.status = "confirmed"
            txn.cat_source = "user"
            txns_updated += 1

            # Create rule if scope includes future
            if apply_scope in ("all_past_and_future",):
                from app.src.services.categoriser import (
                    apply_rule_retroactively,
                    create_rule,
                )
                rule = create_rule(
                    session,
                    match_type="payee",
                    pattern=txn.payee_raw or "",
                    category_id=category_id,
                    created_from="user",
                    priority=20,
                )
                n = apply_rule_retroactively(session, rule)
                txns_updated += n
                rules_created = 1

            elif apply_scope == "all_past":
                # Apply to all historical transactions with same payee
                payee = txn.payee_raw or ""
                if payee:
                    similar = session.query(Transaction).filter(
                        Transaction.payee_raw == payee,
                        Transaction.status.in_(["auto", "pending"]),
                    ).all()
                    for t in similar:
                        t.category_id = category_id
                        t.confidence = Decimal("1.0")
                        t.status = "confirmed"
                        t.cat_source = "user"
                        txns_updated += 1

    # Close all related review items for the same payee
    if item.txn_id:
        txn = session.get(Transaction, item.txn_id)
        payee = txn.payee_raw if txn else None
        if payee:
            sibling_txns = session.query(Transaction).filter_by(payee_raw=payee).all()
            sibling_txn_ids = [t.id for t in sibling_txns]
            siblings = session.query(ReviewItem).filter(
                ReviewItem.txn_id.in_(sibling_txn_ids),
                ReviewItem.status == "open",
            ).all()
            for sib in siblings:
                sib.status = "resolved"
                sib.resolved_at = datetime.utcnow()

    item.status = "resolved"
    item.resolved_at = datetime.utcnow()
    item.resolution_json = json.dumps({"category_id": category_id, "scope": apply_scope})

    session.commit()
    return ResolveResult(resolved=1, rules_created=rules_created, txns_updated=txns_updated)


def resolve_bulk(
    session: Session,
    item_ids: list[int],
    category_id: int | None,
    apply_scope: str,
) -> ResolveResult:
    total = ResolveResult(resolved=0, rules_created=0, txns_updated=0)
    for item_id in item_ids:
        r = resolve(session, item_id, category_id, apply_scope)
        total.resolved += r.resolved
        total.rules_created += r.rules_created
        total.txns_updated += r.txns_updated
    return total


def counts(session: Session) -> dict[str, int]:
    """Count open review items by kind."""
    from sqlalchemy import func
    rows = (
        session.query(ReviewItem.kind, func.count(ReviewItem.id))
        .filter_by(status="open")
        .group_by(ReviewItem.kind)
        .all()
    )
    result = {kind: count for kind, count in rows}
    result["total"] = sum(result.values())
    return result
