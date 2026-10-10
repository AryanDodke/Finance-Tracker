"""
Categoriser: assigns a category to each transaction.
Priority: rule → merchant.default_category → LLM batch → review queue.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.core.setting import settings
from app.src.models.db_models import Category, Merchant, Rule, Transaction


@dataclass
class Categorisation:
    category_id: int | None
    confidence: float
    source: str   # rule | merchant | llm | none


@dataclass
class CategoriseSummary:
    total: int
    auto: int
    pending: int
    review_created: int


def match_rule(session: Session, txn: Transaction) -> Rule | None:
    """Try rules in priority order: payee > merchant > regex > amount_range."""
    rules = session.query(Rule).order_by(Rule.priority.desc()).all()

    for rule in rules:
        if rule.match_type == "payee":
            if txn.payee_raw and rule.pattern.lower() in txn.payee_raw.lower():
                return rule
        elif rule.match_type == "merchant":
            if txn.merchant_id:
                m = session.get(Merchant, txn.merchant_id)
                if m and rule.pattern.lower() in m.canonical_name.lower():
                    return rule
        elif rule.match_type == "regex":
            import re
            if txn.raw_narration and re.search(rule.pattern, txn.raw_narration, re.IGNORECASE):
                return rule
        elif rule.match_type == "amount_range":
            try:
                lo, hi = map(Decimal, rule.pattern.split("-"))
                if lo <= txn.amount <= hi:
                    return rule
            except Exception:
                continue

    return None


def create_rule(
    session: Session,
    match_type: str,
    pattern: str,
    category_id: int,
    created_from: str = "user",
    priority: int = 10,
) -> Rule:
    rule = Rule(
        match_type=match_type,
        pattern=pattern,
        category_id=category_id,
        priority=priority,
        created_from=created_from,
    )
    session.add(rule)
    session.flush()
    return rule


def apply_rule_retroactively(session: Session, rule: Rule) -> int:
    """Apply a rule to all historical matching transactions. Returns rows updated."""
    txns = session.query(Transaction).filter(
        Transaction.status.in_(["auto", "pending"])
    ).all()

    updated = 0
    for txn in txns:
        if match_rule(session, txn) == rule or _rule_matches(rule, txn, session):
            txn.category_id = rule.category_id
            txn.confidence = Decimal("1.0")
            txn.status = "confirmed"
            txn.cat_source = "rule"
            updated += 1

    session.flush()
    return updated


def _rule_matches(rule: Rule, txn: Transaction, session: Session) -> bool:
    if rule.match_type == "payee":
        return bool(txn.payee_raw and rule.pattern.lower() in txn.payee_raw.lower())
    elif rule.match_type == "merchant" and txn.merchant_id:
        m = session.get(Merchant, txn.merchant_id)
        return bool(m and rule.pattern.lower() in m.canonical_name.lower())
    elif rule.match_type == "regex":
        import re
        return bool(txn.raw_narration and re.search(rule.pattern, txn.raw_narration, re.IGNORECASE))
    return False


def categorise_txn(session: Session, txn: Transaction) -> Categorisation:
    """Categorise a single transaction using the priority chain."""

    # 1. Rule match
    rule = match_rule(session, txn)
    if rule:
        return Categorisation(category_id=rule.category_id, confidence=1.0, source="rule")

    # 2. Merchant default category
    if txn.merchant_id:
        merchant = session.get(Merchant, txn.merchant_id)
        if merchant and merchant.default_category_id:
            return Categorisation(
                category_id=merchant.default_category_id,
                confidence=0.95,
                source="merchant",
            )

    # 3. LLM (deferred – handled in batch)
    return Categorisation(category_id=None, confidence=0.0, source="none")


def llm_classify_merchants(session: Session, merchants: list[str]) -> list[dict]:
    """
    Batch-classify merchant names via LLM.
    Returns list of {merchant, category, confidence}.
    """
    if not merchants:
        return []

    categories = [c.name for c in session.query(Category).all()]
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "merchant": {"type": "string"},
                "category": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["merchant", "category", "confidence"],
        },
    }

    system = (
        f"You are a personal finance categoriser. "
        f"Classify each merchant into one of these categories: {', '.join(categories)}. "
        f"Return ONLY a JSON array. Be conservative: if unsure, use 'Uncategorised' with low confidence."
    )
    user = f"Classify these merchants:\n{chr(10).join(f'- {m}' for m in merchants)}"

    try:
        from app.src.language_models.llm.gateway import get_gateway
        gateway = get_gateway()
        result = gateway.run(system, user, schema)
        if isinstance(result, list):
            return result
        return []
    except Exception as e:
        logger.warning(f"LLM classification failed: {e}")
        return []


def route_result(session: Session, txn: Transaction, result: Categorisation) -> None:
    """Apply categorisation result or create review item."""
    from app.src.services.review_queue import create_review_item

    if result.category_id and result.confidence >= settings.categorisation_confidence_threshold:
        txn.category_id = result.category_id
        txn.confidence = Decimal(str(result.confidence))
        txn.status = "auto"
        txn.cat_source = result.source
    elif result.category_id and result.confidence > 0:
        # Low confidence: auto but flag for review
        txn.category_id = result.category_id
        txn.confidence = Decimal(str(result.confidence))
        txn.status = "pending"
        txn.cat_source = result.source
        create_review_item(
            session, "low_conf",
            txn_id=txn.id,
            question=f"Confirm category for: {txn.payee_raw or txn.raw_narration[:50]}?",
            options=_category_options(session),
        )
    else:
        # Unknown payee
        txn.status = "pending"
        if txn.merchant_id:
            from app.src.models.db_models import Merchant
            m = session.get(Merchant, txn.merchant_id)
            if m and m.is_person:
                create_review_item(
                    session, "unknown_payee",
                    txn_id=txn.id,
                    question=f"Who is '{txn.payee_raw}'? What category should their payments go to?",
                    options=_category_options(session),
                )
                return
        create_review_item(
            session, "unknown_payee",
            txn_id=txn.id,
            question=f"What category is '{txn.payee_raw or txn.raw_narration[:50]}'?",
            options=_category_options(session),
        )


def _category_options(session: Session) -> list[dict]:
    cats = session.query(Category).all()
    return [{"label": c.name, "value": c.id} for c in cats]


def categorise_batch(session: Session, txn_ids: list[int]) -> CategoriseSummary:
    """
    Categorise a batch of transactions.
    First tries rule/merchant, then batches unknowns to LLM.
    """
    txns = session.query(Transaction).filter(Transaction.id.in_(txn_ids)).all()
    summary = CategoriseSummary(total=len(txns), auto=0, pending=0, review_created=0)

    unknown_merchants: list[tuple[Transaction, str]] = []

    for txn in txns:
        result = categorise_txn(session, txn)
        if result.category_id:
            route_result(session, txn, result)
            if txn.status == "auto":
                summary.auto += 1
            else:
                summary.pending += 1
        else:
            # Collect for LLM batch
            merchant_name = ""
            if txn.merchant_id:
                m = session.get(Merchant, txn.merchant_id)
                merchant_name = m.canonical_name if m else ""
            unknown_merchants.append((txn, merchant_name or txn.payee_raw or ""))

    # Batch LLM for unknowns
    if unknown_merchants:
        merchant_names = list({name for _, name in unknown_merchants if name})
        llm_results = llm_classify_merchants(session, merchant_names)

        # Build lookup: merchant_name → (category_name, confidence)
        llm_lookup: dict[str, tuple[str, float]] = {}
        for r in llm_results:
            llm_lookup[r["merchant"].lower()] = (r["category"], float(r["confidence"]))

        for txn, merchant_name in unknown_merchants:
            cat_name, conf = llm_lookup.get(merchant_name.lower(), (None, 0.0))
            if cat_name:
                cat = session.query(Category).filter_by(name=cat_name).first()
                if cat:
                    # Cache on merchant
                    if txn.merchant_id:
                        m = session.get(Merchant, txn.merchant_id)
                        if m and not m.default_category_id:
                            m.default_category_id = cat.id
                    result = Categorisation(category_id=cat.id, confidence=conf, source="llm")
                    route_result(session, txn, result)
                    if txn.status == "auto":
                        summary.auto += 1
                    else:
                        summary.pending += 1
                    continue
            route_result(session, txn, Categorisation(None, 0.0, "none"))
            summary.pending += 1

    session.commit()
    logger.info(f"Categorised {summary.total}: {summary.auto} auto, {summary.pending} pending")
    return summary
