"""
Notes parser: turn Apple Notes text into structured note lines.
Uses regex first (if format matches), LLM as fallback.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.src.models.db_models import Category, NoteLine


@dataclass
class ParsedLine:
    item_text: str
    amount: Decimal
    category: str | None


# ─── Regex parser ────────────────────────────────────────────────────────────

_AMOUNT_RE = re.compile(r"(?:₹\s*|Rs\.?\s*)?(\d[\d,]*(?:\.\d+)?)")
_SECTION_RE = re.compile(
    r"^(Personal|Travel|Home\s*Expense|Outing|Food|Rent)[:\-–]?\s*$",
    re.IGNORECASE,
)


def _parse_amount(s: str) -> Decimal | None:
    m = _AMOUNT_RE.search(s)
    if m:
        try:
            return Decimal(m.group(1).replace(",", ""))
        except InvalidOperation:
            return None
    return None


def regex_parse_notes(text: str) -> list[ParsedLine]:
    """
    Parse a month's notes using the known category heading format:
    
    Personal:
      Rent - 12000
      Food - 8000
    Travel:
      Train - 2000
    """
    lines = text.splitlines()
    results: list[ParsedLine] = []
    current_category: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        section_match = _SECTION_RE.match(stripped)
        if section_match:
            current_category = section_match.group(1).title()
            continue

        # Try to parse an item line: "Item Name - Amount" or "Item Name : Amount"
        m = re.match(r"^(.+?)[\s\-:–]+(\d[\d,.]+)\s*$", stripped)
        if m:
            item = m.group(1).strip()
            amount = _parse_amount(m.group(2))
            if amount and amount > 0:
                results.append(ParsedLine(
                    item_text=item,
                    amount=amount,
                    category=current_category,
                ))

    return results


def llm_parse_notes(text: str, period: str, session: Session) -> list[ParsedLine]:
    """Use LLM to parse notes when regex can't handle the format."""
    categories = [c.name for c in session.query(Category).all()]
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "amount": {"type": "number"},
                "category": {"type": "string"},
            },
            "required": ["item", "amount"],
        },
    }
    system = (
        f"You are parsing a personal finance note for {period}. "
        f"Extract every spending line item with its amount and best-fit category from: {', '.join(categories)}. "
        f"Return ONLY a JSON array."
    )
    user = f"Notes:\n{text}"

    try:
        from app.src.language_models.llm.gateway import get_gateway
        gateway = get_gateway()
        result = gateway.run(system, user, schema)
        if isinstance(result, list):
            lines = []
            for r in result:
                try:
                    amt = Decimal(str(r["amount"]))
                    if amt > 0:
                        lines.append(ParsedLine(
                            item_text=str(r["item"]),
                            amount=amt,
                            category=r.get("category"),
                        ))
                except Exception:
                    continue
            return lines
    except Exception as e:
        logger.warning(f"LLM notes parse failed: {e}")
    return []


def ingest_notes(
    session: Session,
    text: str,
    period: str,
    source_file_id: int,
) -> int:
    """Parse notes and store as NoteLine rows. Returns count of lines inserted."""

    # Try regex first
    parsed = regex_parse_notes(text)
    if not parsed:
        logger.info("Regex parse yielded no lines, trying LLM...")
        parsed = llm_parse_notes(text, period, session)

    if not parsed:
        logger.warning(f"Could not parse notes for {period}")
        return 0

    # Delete existing note lines for this period/source (idempotent)
    session.query(NoteLine).filter_by(period=period, source_file_id=source_file_id).delete()

    inserted = 0
    for p in parsed:
        # Resolve category
        cat_id = None
        if p.category:
            cat = session.query(Category).filter(
                Category.name.ilike(p.category)
            ).first()
            if cat:
                cat_id = cat.id

        note_line = NoteLine(
            period=period,
            item_text=p.item_text,
            amount=p.amount,
            category_id=cat_id,
            source_file_id=source_file_id,
        )
        session.add(note_line)
        inserted += 1

    session.commit()
    logger.info(f"Inserted {inserted} note lines for {period}")
    return inserted
