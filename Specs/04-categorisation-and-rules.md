# 04 Categorisation and Rules

## Purpose
Assign a category to each transaction using the cheapest reliable method first: user rules, then merchant default, then LLM, then ask the user.

## Files
- `services/categoriser.py`
- `services/rules.py`
- `routers/transactions.py`: `GET /transactions`, `PATCH /transactions/{id}`.

## Function definitions
```python
# rules.py
def match_rule(session: Session, txn: Transaction) -> Rule | None: ...        # priority order
def create_rule(session: Session, match_type: str, pattern: str, category_id: int, created_from: str) -> Rule: ...
def apply_rule_retroactively(session: Session, rule: Rule) -> int: ...        # returns rows updated

# categoriser.py
@dataclass
class Categorisation:
    category_id: int | None; confidence: float; source: str   # rule|merchant|llm|none

def categorise_txn(session: Session, txn: Transaction) -> Categorisation: ...
def categorise_batch(session: Session, txn_ids: list[int]) -> CategoriseSummary: ...
def llm_classify_merchants(merchants: list[str]) -> list[MerchantGuess]: ...   # via 05 gateway, batched
def route_result(session: Session, txn: Transaction, result: Categorisation) -> None: ...  # auto vs review item
```

## Decision order
1. `match_rule` (conf 1.0) 2. `merchant.default_category` (0.95) 3. batched LLM (model conf) 4. if `conf >= 0.8` set `status=auto`, else create `review_item(low_conf)`. Person payees always create `unknown_payee` review items.

## Communication
- Calls: `03` (merchant), `05.gateway.run` (via `llm_classify_merchants`), `08.review_queue.create_item`.
- Called by: `02.ingestion`, `08` (after answers), `PATCH /transactions/{id}`.
- Writes: `transaction.category_id/confidence/status`, `rule`, `merchant.default_category_id`.

## Tasks
1. Rule engine with priorities (payee > merchant > regex > amount range).
2. Batch LLM prompt: merchants in, strict JSON out, schema validated.
3. Confidence routing and review item creation.
4. Manual re-categorise endpoint with `apply_scope` (this one / all past / all future).
5. Self-transfer and credit handling (`Transfer`, `Income`).

## Acceptance
- A merchant is sent to an LLM at most once ever (cached to `merchant.default_category_id`). After the first review session, 90%+ of rows have a category. Retroactive rule application updates all matching rows.
