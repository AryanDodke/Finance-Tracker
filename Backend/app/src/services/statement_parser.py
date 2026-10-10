"""
Statement parser: unlock SBI PDF, extract rows, detect layout, merge continuation rows.
Uses pikepdf (unlock) + pdfplumber (extract tables).
"""
from __future__ import annotations

import hashlib
import re
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.core.logger import logger


@dataclass
class RawTxn:
    date: str                       # ISO date YYYY-MM-DD
    narration: str
    ref_no: str | None
    debit: Decimal | None
    credit: Decimal | None
    balance: Decimal | None


def unlock_pdf(path: Path, password: str) -> Path:
    """Decrypt password-protected PDF, save to temp file, return new path."""
    from pypdf import PdfReader, PdfWriter
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()
    out_path = Path(tmp.name)
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            success = reader.decrypt(password)
            if not success:
                raise ValueError("Incorrect PDF password.")
        
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
            
        with open(out_path, "wb") as f:
            writer.write(f)
    except Exception as e:
        if "Incorrect" in str(e):
            raise
        raise ValueError(f"Could not open PDF: {e}") from e
    return out_path


def _parse_amount(val: str) -> Decimal | None:
    """Parse Indian number format. Returns None for empty/dash."""
    if not val:
        return None
    cleaned = re.sub(r"[,\s]", "", str(val)).strip()
    if cleaned in ("", "-", "NIL"):
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_date(val: str) -> str | None:
    """Try common SBI date formats → YYYY-MM-DD."""
    val = val.strip()
    for fmt in ("%d %b %Y", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%d %b %y"):
        try:
            from datetime import datetime
            return datetime.strptime(val, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# Column header aliases for SBI statements
_DATE_KEYS = {"date", "txn date", "value date", "transaction date"}
_NARRATION_KEYS = {"description", "narration", "particulars", "details"}
_REF_KEYS = {"ref no", "cheque no", "reference no", "ref / cheque no"}
_DEBIT_KEYS = {"debit", "withdrawal", "dr", "withdrawal amt"}
_CREDIT_KEYS = {"credit", "deposit", "cr", "deposit amt"}
_BALANCE_KEYS = {"balance", "closing balance"}


def detect_layout(headers: list[str]) -> dict[str, int]:
    """Map semantic column names to header indices."""
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        norm = h.lower().strip()
        if norm in _DATE_KEYS:
            mapping.setdefault("date", i)
        elif norm in _NARRATION_KEYS:
            mapping.setdefault("narration", i)
        elif norm in _REF_KEYS:
            mapping.setdefault("ref", i)
        elif norm in _DEBIT_KEYS:
            mapping.setdefault("debit", i)
        elif norm in _CREDIT_KEYS:
            mapping.setdefault("credit", i)
        elif norm in _BALANCE_KEYS:
            mapping.setdefault("balance", i)
    return mapping


def merge_continuation_rows(rows: list[list]) -> list[list]:
    """Merge rows where the date column is empty (multi-line narrations)."""
    merged: list[list] = []
    for row in rows:
        if not row:
            continue
        date_val = str(row[0]).strip() if row[0] else ""
        if merged and not date_val:
            # Continuation: append narration to previous row
            if len(merged[-1]) > 1 and len(row) > 1:
                merged[-1][1] = str(merged[-1][1] or "") + " " + str(row[1] or "")
        else:
            merged.append(list(row))
    return merged


def extract_rows(pdf_path: Path) -> tuple[list[RawTxn], list[dict]]:
    """
    Extract transactions from unlocked PDF.
    Returns (list[RawTxn], list[parse_errors]).
    """
    import pdfplumber

    raw_txns: list[RawTxn] = []
    errors: list[dict] = []

    with pdfplumber.open(pdf_path) as pdf:
        layout: dict[str, int] | None = None
        all_rows: list[list] = []

        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                # First non-empty row might be headers
                for row in table:
                    if not any(row):
                        continue
                    if layout is None:
                        candidate = detect_layout([str(c or "") for c in row])
                        if "date" in candidate and "narration" in candidate:
                            layout = candidate
                            continue   # skip header row
                    all_rows.append([str(c or "").strip() for c in row])

        if layout is None:
            errors.append({"page": 0, "raw": "", "reason": "Could not detect column layout"})
            return raw_txns, errors

        # Merge continuation rows
        merged = merge_continuation_rows(all_rows)

        for row in merged:
            try:
                if len(row) <= max(layout.values()):
                    continue

                date_str = _parse_date(row[layout["date"]])
                if not date_str:
                    continue

                narration = row[layout.get("narration", 1)].strip()
                ref_no = row[layout["ref"]].strip() if "ref" in layout else None
                debit = _parse_amount(row[layout["debit"]]) if "debit" in layout else None
                credit = _parse_amount(row[layout["credit"]]) if "credit" in layout else None
                balance = _parse_amount(row[layout["balance"]]) if "balance" in layout else None

                if debit is None and credit is None:
                    continue  # balance-only row

                raw_txns.append(RawTxn(
                    date=date_str,
                    narration=narration,
                    ref_no=ref_no or None,
                    debit=debit,
                    credit=credit,
                    balance=balance,
                ))
            except Exception as e:
                errors.append({"page": 0, "raw": str(row), "reason": str(e)})

    logger.info(f"Extracted {len(raw_txns)} transactions, {len(errors)} errors from PDF.")
    return raw_txns, errors


def compute_txn_hash(date: str, amount: Decimal, upi_ref: str | None, narration: str) -> str:
    """Stable deduplication hash."""
    raw = f"{date}|{amount}|{upi_ref or ''}|{narration}"
    return hashlib.sha256(raw.encode()).hexdigest()
