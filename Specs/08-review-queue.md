# 08 Review Queue (Human in the Loop)

## Purpose
Collect everything the system cannot decide, ask the user in batches, and turn each answer into a permanent rule.

## Files
- `services/review_queue.py`
- `routers/review.py`: `GET /review`, `POST /review/{id}/resolve`, `POST /review/bulk-resolve`.

## Item kinds
`unknown_payee`, `low_conf`, `unmatched_note`, `unmatched_txn`, `amount_gap`, `category_conflict`.

## Function definitions
```python
def create_item(session: Session, kind: str, *, txn_id: int | None = None,
                note_line_id: int | None = None, question: str, options: list[Option]) -> ReviewItem: ...  # dedupes
def list_open(session: Session, group_by: str = "payee") -> list[ReviewGroup]: ...   # unknown payees first
def resolve(session: Session, item_id: int, answer: Answer, apply_scope: str) -> ResolveResult: ...
def resolve_bulk(session: Session, item_ids: list[int], answer: Answer, apply_scope: str) -> ResolveResult: ...
def skip(session: Session, item_id: int) -> None: ...
def counts(session: Session) -> dict[str, int]: ...
```
`apply_scope`: `this_only` | `all_past` | `all_past_and_future` (creates a rule).

## Resolve effects
- `unknown_payee` / `low_conf`: set transaction category, create `rule` (if scope includes future), call `04.apply_rule_retroactively`, close all sibling items for that payee.
- `unmatched_*`: link note line to a txn, or mark "cash / not in bank / ignore".
- `amount_gap`: mark explained (with optional note) or fix categorisation.

## Communication
- Called by: `04`, `07` (create), `routers/review.py` (resolve).
- Calls: `04.rules` (create_rule, apply_rule_retroactively), `03.merge_merchants`, `07.reconcile_period` (refresh after changes).
- Writes: `review_item`, `rule`, `transaction`.

## Tasks
1. Dedupe logic (same payee, one item). Grouping and ordering by impact (rows affected).
2. Resolve handlers per kind, transactional.
3. Bulk answer endpoint. Undo last resolution (store before-state).

## Acceptance
- Answering "Ramesh K is Rent" once recategorises every historical and future payment to that payee and closes all related items.
