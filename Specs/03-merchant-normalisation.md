# 03 Merchant Normalisation

## Purpose
Collapse noisy payee strings ("SWIGGY*BLR 12345", "Swiggy Instamart") into one canonical `merchant`, so rules and cache work.

## Files
- `services/merchant_normaliser.py`

## Function definitions
```python
def clean_name(raw: str) -> str: ...                       # lowercase, strip digits, location codes, noise tokens
def find_merchant(session: Session, cleaned: str) -> Merchant | None: ...   # exact alias, then fuzzy
def fuzzy_match(cleaned: str, candidates: list[str], threshold: int = 90) -> str | None: ...  # rapidfuzz
def get_or_create_merchant(session: Session, raw: str, is_person: bool) -> Merchant: ...
def add_alias(session: Session, merchant_id: int, alias: str) -> None: ...
def merge_merchants(session: Session, keep_id: int, drop_id: int) -> None: ...   # user-driven cleanup
def normalise_batch(session: Session, txn_ids: list[int]) -> None: ...      # sets transaction.merchant_id
```

## Communication
- Called by: `02.ingestion` (post-persist), `08.review_queue` (merchant merge answers).
- Calls: `01` models, `02.upi_narration` output (`payee_raw`, `is_person`).
- Writes: `merchant`, `transaction.merchant_id`.

## Tasks
1. Noise token list (UPI, PVT, LTD, city codes), kept in a config file.
2. Alias table and fuzzy matching with a safety threshold.
3. Person vs merchant flag carried from the narration parser.
4. Merge tool: re-point transactions, union aliases.

## Acceptance
- Variants of the same merchant resolve to one row. Fuzzy matches never merge clearly different merchants (test with confusable pairs).
