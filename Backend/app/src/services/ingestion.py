"""
Ingestion orchestrator: handles upload, dedupe, persistence, and kicks off normalisation + categorisation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.setting import settings
from app.src.models.db_models import ParseError, SourceFile, Transaction
from app.src.services.statement_parser import (
    RawTxn,
    compute_txn_hash,
    extract_rows,
    unlock_pdf,
)
from app.src.services.upi_narration import parse_upi_narration


@dataclass
class IngestResult:
    source_file_id: int
    period: str
    inserted: int
    skipped: int
    errors: int
    message: str


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _save_upload(file_bytes: bytes, filename: str) -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    dest.write_bytes(file_bytes)
    return dest


def persist_transactions(
    session: Session,
    raws: list[RawTxn],
    source_file_id: int,
    errors: list[dict],
) -> tuple[int, int]:
    """Insert deduplicated transactions. Returns (inserted, skipped)."""
    inserted = 0
    skipped = 0

    for raw in raws:
        amount = raw.debit or raw.credit or Decimal("0")
        direction = "debit" if raw.debit else "credit"

        upi = parse_upi_narration(raw.narration)
        txn_hash = compute_txn_hash(raw.date, amount, upi.upi_ref or raw.ref_no, raw.narration)

        # Dedupe
        existing = session.query(Transaction).filter_by(txn_hash=txn_hash).first()
        if existing:
            skipped += 1
            continue

        # Determine category for self-transfers immediately
        cat_id = None
        status = "pending"
        if upi.is_self_transfer:
            # Look up Transfer category
            from app.src.models.db_models import Category
            transfer_cat = session.query(Category).filter_by(name="Transfer").first()
            if transfer_cat:
                cat_id = transfer_cat.id
                status = "auto"

        txn = Transaction(
            txn_hash=txn_hash,
            txn_date=raw.date,
            amount=amount,
            direction=direction,
            raw_narration=raw.narration,
            upi_ref=upi.upi_ref or raw.ref_no,
            upi_handle=upi.upi_handle,
            payee_raw=upi.payee_name or raw.narration[:200],
            category_id=cat_id,
            confidence=Decimal("1.0") if cat_id else Decimal("0.0"),
            status=status,
            cat_source="rule" if cat_id else None,
            source_file_id=source_file_id,
        )
        session.add(txn)
        inserted += 1

    # Store parse errors
    for err in errors:
        pe = ParseError(
            source_file_id=source_file_id,
            page=err.get("page"),
            raw_text=err.get("raw", "")[:2000],
            reason=err.get("reason", "")[:500],
        )
        session.add(pe)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # Retry row-by-row to handle partial conflicts
        for txn in session.new:
            try:
                session.add(txn)
                session.commit()
                inserted += 1
            except IntegrityError:
                session.rollback()
                skipped += 1

    return inserted, skipped


async def ingest_statement(
    session: Session,
    file_bytes: bytes,
    filename: str,
    password: str,
    period: str,
) -> IngestResult:
    """Full ingestion pipeline: save → hash dedupe → unlock → parse → persist → normalise → categorise."""
    # Save file
    saved_path = _save_upload(file_bytes, filename)
    file_hash = file_sha256(saved_path)

    # Dedupe by file hash
    existing_file = session.query(SourceFile).filter_by(file_hash=file_hash).first()
    if existing_file:
        return IngestResult(
            source_file_id=existing_file.id,
            period=existing_file.period,
            inserted=0,
            skipped=0,
            errors=0,
            message="Already ingested. No new rows.",
        )

    # Record file
    source_file = SourceFile(
        kind="bank_pdf",
        file_hash=file_hash,
        period=period,
        original_name=filename,
    )
    session.add(source_file)
    session.flush()

    # Unlock
    try:
        unlocked_path = unlock_pdf(saved_path, password)
    except ValueError:
        session.rollback()
        raise

    # Extract
    raw_txns, parse_errors = extract_rows(unlocked_path)

    # Persist
    inserted, skipped = persist_transactions(session, raw_txns, source_file.id, parse_errors)

    # Kick off normalisation + categorisation
    txn_ids = [
        t.id for t in session.query(Transaction)
        .filter_by(source_file_id=source_file.id)
        .all()
    ]
    if txn_ids:
        from app.src.services.merchant_normaliser import normalise_batch
        normalise_batch(session, txn_ids)

        from app.src.services.categoriser import categorise_batch
        categorise_batch(session, txn_ids)

    return IngestResult(
        source_file_id=source_file.id,
        period=period,
        inserted=inserted,
        skipped=skipped,
        errors=len(parse_errors),
        message=f"Ingested {inserted} transactions ({skipped} duplicates, {len(parse_errors)} parse errors).",
    )
