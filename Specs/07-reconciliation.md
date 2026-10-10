# 07 Reconciliation (Notes vs Bank)

## Purpose
Compare each month's notes with the bank truth: match individual items where possible, then compare category totals, and surface where the notes were inaccurate.

## Files
- `services/reconciler.py`
- `routers/reconcile.py`: `GET /reconcile/{period}`.

## Function definitions
```python
def reconcile_period(session: Session, period: str) -> ReconcileReport: ...
def candidate_txns(session: Session, period: str) -> list[Transaction]: ...     # debits in month, not Transfer
def score_match(note: NoteLine, txn: Transaction) -> float: ...                  # 0.6 amount + 0.3 text + 0.1 category
def match_items(notes: list[NoteLine], txns: list[Transaction], threshold: float = 0.7) -> list[Match]: ...  # greedy one-to-one
def category_totals(session: Session, period: str) -> dict[int, TotalsPair]: ... # noted vs bank
def detect_gaps(totals: dict, pct: float = 0.10, abs_amt: Decimal = Decimal("500")) -> list[Gap]: ...
def create_reconcile_review_items(session: Session, report: ReconcileReport) -> int: ...
```

## Outputs (`ReconcileReport`)
- `matched`: note line to txn pairs with scores.
- `unmatched_notes`: in notes, not in bank (cash? typo?).
- `unmatched_txns`: in bank, not in notes (forgotten).
- `category_gaps`: per-category noted vs actual with difference and accuracy %.

## Communication
- Calls: `01` models, `08.review_queue.create_item` (kinds: `unmatched_note`, `unmatched_txn`, `amount_gap`).
- Called by: `06.ingest_notes`, `04` (after bulk recategorisation, to recompute), `routers/reconcile.py`.
- Writes: `note_line.matched_txn_id/match_score`, `review_item`.
- Read by: `09.insights` (notes accuracy score), `11.frontend` Compare page.

## Rules
Bank category wins. If a matched note category disagrees with the bank category, ask the user once and offer to create a rule.

## Tasks
1. Scoring function with tests on synthetic pairs.
2. Greedy assignment, then optional Hungarian algorithm upgrade if greedy misfires.
3. Category totals and gap detection with thresholds in config.
4. Review item creation (deduplicated across reruns).

## Acceptance
- Re-running reconcile is idempotent. A planted ₹ mismatch shows as an `amount_gap` and a planted missing item as `unmatched_txn`.
