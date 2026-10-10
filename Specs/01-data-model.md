# 01 Data Model

## Purpose
Single source of schema truth. Every other feature reads and writes through these models.

## Files
- `backend/app/db.py`: engine, `SessionLocal`, `get_session()` dependency.
- `backend/app/models.py`: SQLAlchemy models.
- `backend/app/schemas.py`: Pydantic read/write schemas.
- `backend/alembic/`: migrations (or `create_all` for MVP).

## Tables
| Table | Key columns | Notes |
|---|---|---|
| `source_file` | id, kind(bank_pdf/notes), file_hash UK, period YYYY-MM, ingested_at | dedupe uploads |
| `transaction` | id, txn_hash UK, txn_date, amount Numeric(12,2), direction, raw_narration, upi_ref, payee_raw, merchant_id, category_id, confidence, status(auto/confirmed/pending), source_file_id | bank rows |
| `merchant` | id, canonical_name UK, aliases_json, default_category_id, is_person | normalised entities |
| `category` | id, name, parent_id | seeded at startup |
| `rule` | id, match_type(payee/merchant/regex/amount_range), pattern, category_id, priority, created_from(user/llm) | learned rules |
| `note_line` | id, period, item_text, amount, category_id, matched_txn_id, match_score | parsed notes |
| `review_item` | id, kind, txn_id, note_line_id, question, options_json, status | questions for user |
| `budget` | id, category_id, monthly_amount, effective_from | plus income row |
| `parse_error` | id, source_file_id, page, raw_text, reason | nothing dropped silently |
| `llm_usage` | id, provider, date, calls, failures | rate-limit tracking |

## Function definitions
```python
# db.py
def get_session() -> Iterator[Session]: ...
def init_db() -> None: ...                 # create tables + seed categories

# models helpers
def seed_categories(session: Session) -> None: ...
def compute_txn_hash(date: date, amount: Decimal, upi_ref: str | None, narration: str) -> str: ...
```

## Communication
- Imported by: all services and routers.
- Imports: nothing from other features (leaf module).

## Tasks
1. Define models and constraints (unique hashes, FK indexes on date, category, merchant, period).
2. Seed categories (4 user categories + sub-categories Rent/Food + Transfer/Income/Uncategorised).
3. Pydantic schemas: `TxnOut`, `TxnPatch`, `ReviewItemOut`, `RuleIn`, etc.
4. Migration setup.

## Acceptance
- `init_db()` is idempotent. Inserting the same `txn_hash` twice is rejected cleanly. All money columns are `Numeric(12,2)`.
