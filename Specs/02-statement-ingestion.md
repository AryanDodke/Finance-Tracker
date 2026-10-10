# 02 Statement Ingestion (SBI PDF to clean transactions)

## Purpose
Turn password-protected SBI statement PDFs into deduplicated `transaction` rows with structured UPI details.

## Files
- `services/statement_parser.py`: unlock, extract, map columns.
- `services/upi_narration.py`: parse SBI UPI narration strings.
- `services/ingestion.py`: orchestrates upload, dedupe, persistence.
- `routers/upload.py`: `POST /upload/statement`.

## Function definitions
```python
# statement_parser.py
@dataclass
class RawTxn:
    date: date; narration: str; ref_no: str | None
    debit: Decimal | None; credit: Decimal | None; balance: Decimal | None

def unlock_pdf(path: Path, password: str) -> Path: ...                 # pikepdf
def extract_rows(pdf_path: Path) -> list[RawTxn]: ...                  # pdfplumber tables
def detect_layout(pdf_path: Path) -> LayoutSpec: ...                   # column positions / header names
def merge_continuation_rows(rows: list[dict]) -> list[dict]: ...       # multi-line narrations

# upi_narration.py
@dataclass
class UpiInfo:
    payee_name: str | None; upi_handle: str | None; upi_ref: str | None
    remark: str | None; is_person: bool; is_self_transfer: bool

def parse_upi_narration(narration: str) -> UpiInfo: ...
def looks_like_person(name: str, handle: str | None) -> bool: ...

# ingestion.py
def ingest_statement(session: Session, file: UploadFile, password: str) -> IngestResult: ...
def file_sha256(path: Path) -> str: ...
def persist_transactions(session: Session, raws: list[RawTxn], source_file_id: int) -> tuple[int, int]: ...  # (inserted, skipped)
```

## Flow
`router.upload` to `ingestion.ingest_statement` to `unlock_pdf` to `extract_rows` to `parse_upi_narration` per row to `persist_transactions` to enqueue for [03 normalisation](03-merchant-normalisation.md) then [04 categorisation](04-categorisation-and-rules.md).

## Communication
- Calls: `01` (models, hash), `03.normalise_batch`, `04.categorise_batch` (post-ingest hook).
- Called by: `routers/upload.py`.
- Writes: `source_file`, `transaction`, `parse_error`.

## Errors
- Wrong password gives HTTP 422 with a clear message. Unparseable rows go to `parse_error` and the file is still partially ingested. Duplicate file hash returns "already ingested".

## Tasks
1. Build against the real redacted sample. Lock column mapping.
2. Narration regexes for SBI UPI (payee, handle, ref, remark). Table-driven so patterns are easy to add.
3. Debit vs credit logic, self-transfer detection.
4. Dedupe by `file_hash` and `txn_hash`.
5. Router and `IngestResult` schema (counts, errors).

## Acceptance
- Row count and debit/credit totals match the PDF summary. Re-upload inserts 0 rows. Golden-file tests pass.
