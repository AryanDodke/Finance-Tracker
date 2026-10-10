"""
Merchant normaliser: collapses noisy payee strings into canonical Merchant rows.
Steps: clean → exact alias → fuzzy match → create pending merchant.
"""
from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.core.setting import settings
from app.src.models.db_models import Merchant, Transaction

# ─── Noise tokens to strip ───────────────────────────────────────────────────

_NOISE_TOKENS = {
    "upi", "pvt", "ltd", "llp", "inc", "corp", "limited", "private",
    "technologies", "tech", "solutions", "services", "india",
    "payment", "payments", "pay", "online", "digital",
    # Location codes
    "blr", "mum", "del", "hyd", "che", "pune", "kol", "ban", "bangalore",
    "mumbai", "delhi", "hyderabad", "chennai",
}

_LOCATION_RE = re.compile(
    r"\b(bangalore|mumbai|delhi|hyderabad|chennai|pune|kolkata|bengaluru)\b",
    re.IGNORECASE,
)
_DIGITS_RE = re.compile(r"\b\d+\b")
_SPECIAL_RE = re.compile(r"[^a-z0-9\s]")
_MULTI_SPACE = re.compile(r"\s+")


def clean_name(raw: str) -> str:
    """Lowercase, strip digits, location codes, noise tokens, punctuation."""
    s = raw.lower()
    s = _LOCATION_RE.sub("", s)
    s = _SPECIAL_RE.sub(" ", s)
    s = _DIGITS_RE.sub(" ", s)
    # Remove noise tokens
    words = s.split()
    words = [w for w in words if w not in _NOISE_TOKENS and len(w) > 1]
    s = _MULTI_SPACE.sub(" ", " ".join(words)).strip()
    return s


def fuzzy_match(cleaned: str, candidates: list[str], threshold: int | None = None) -> str | None:
    """Return best matching candidate above threshold using rapidfuzz."""
    if not candidates or not cleaned:
        return None
    threshold = threshold or settings.fuzzy_merchant_threshold
    try:
        from rapidfuzz import fuzz, process
        result = process.extractOne(cleaned, candidates, scorer=fuzz.token_sort_ratio)
        if result and result[1] >= threshold:
            return result[0]
    except ImportError:
        logger.warning("rapidfuzz not installed; skipping fuzzy match")
    return None


def find_merchant(session: Session, cleaned: str) -> Merchant | None:
    """Exact alias lookup, then fuzzy match against known merchants."""
    if not cleaned:
        return None

    # Exact canonical name
    m = session.query(Merchant).filter(
        Merchant.canonical_name == cleaned
    ).first()
    if m:
        return m

    # Search aliases
    all_merchants = session.query(Merchant).all()
    for m in all_merchants:
        if cleaned in m.aliases:
            return m

    # Fuzzy against canonical names
    canonical_names = [m.canonical_name for m in all_merchants]
    best = fuzzy_match(cleaned, canonical_names)
    if best:
        return next((m for m in all_merchants if m.canonical_name == best), None)

    # Fuzzy against all aliases
    alias_to_merchant: dict[str, Merchant] = {}
    for m in all_merchants:
        for alias in m.aliases:
            alias_to_merchant[alias] = m
    best_alias = fuzzy_match(cleaned, list(alias_to_merchant.keys()))
    if best_alias:
        return alias_to_merchant[best_alias]

    return None


def get_or_create_merchant(session: Session, raw: str, is_person: bool) -> Merchant:
    """Find or create a merchant for the given raw payee string."""
    cleaned = clean_name(raw)
    existing = find_merchant(session, cleaned)
    if existing:
        # Add alias if new
        aliases = existing.aliases
        if cleaned not in aliases and cleaned != existing.canonical_name:
            aliases.append(cleaned)
            existing.aliases = aliases
        return existing

    # Create new merchant
    merchant = Merchant(
        canonical_name=cleaned or raw.lower()[:200],
        aliases_json=json.dumps([cleaned] if cleaned != (raw.lower()[:200]) else []),
        is_person=is_person,
    )
    session.add(merchant)
    session.flush()
    logger.debug(f"Created merchant: {merchant.canonical_name}")
    return merchant


def add_alias(session: Session, merchant_id: int, alias: str) -> None:
    """Add an alias string to a merchant."""
    m = session.get(Merchant, merchant_id)
    if m:
        aliases = m.aliases
        if alias not in aliases:
            aliases.append(alias)
            m.aliases = aliases


def merge_merchants(session: Session, keep_id: int, drop_id: int) -> None:
    """Re-point all transactions from drop_id to keep_id, then delete drop_id."""
    keep = session.get(Merchant, keep_id)
    drop = session.get(Merchant, drop_id)
    if not keep or not drop:
        return

    # Union aliases
    combined = list(set(keep.aliases + drop.aliases + [drop.canonical_name]))
    keep.aliases = combined

    # Re-point transactions
    session.query(Transaction).filter(Transaction.merchant_id == drop_id).update(
        {"merchant_id": keep_id}
    )
    session.delete(drop)
    session.flush()


def normalise_batch(session: Session, txn_ids: list[int]) -> None:
    """Set transaction.merchant_id for a batch of transaction IDs."""
    txns = session.query(Transaction).filter(Transaction.id.in_(txn_ids)).all()
    for txn in txns:
        if txn.merchant_id:
            continue  # already normalised
        raw = txn.payee_raw or txn.raw_narration or ""
        if not raw:
            continue
        # is_person flag stored from UPI parse – check narration for quick lookup
        # (We use a heuristic; the UPI parser already sets payee_raw correctly)
        from app.src.services.upi_narration import looks_like_person
        is_person = looks_like_person(raw, None)
        merchant = get_or_create_merchant(session, raw, is_person)
        txn.merchant_id = merchant.id

    session.commit()
