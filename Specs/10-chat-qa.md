# 10 Chat Q&A

## Purpose
Answer natural-language questions ("how much on food delivery last quarter?") safely, without giving the LLM raw SQL access or the full ledger.

## Files
- `services/qa.py`
- `routers/chat.py`: `POST /chat`.

## Function definitions
```python
class QuerySpec(BaseModel):
    metric: Literal["sum", "count", "avg", "max", "list"]
    group_by: list[Literal["category", "merchant", "month", "weekday"]] = []
    filters: Filters            # date range, categories, merchants, min/max amount
    limit: int = 20

def question_to_spec(question: str, today: date) -> QuerySpec: ...         # LLM via 05, schema-validated
def validate_spec(spec: QuerySpec) -> QuerySpec: ...                        # whitelist fields, cap limits
def execute_spec(session: Session, spec: QuerySpec) -> QueryResult: ...    # SQLAlchemy, no raw SQL
def narrate(question: str, result: QueryResult) -> ChatAnswer: ...         # LLM sees aggregates only
def answer(session: Session, question: str) -> ChatAnswer: ...
```

## Communication
- Calls: `05.gateway`, `09.insights` helpers, `01` models.
- Called by: `routers/chat.py`. Read by: `11.frontend` Chat page.

## Tasks
1. Query spec schema and few-shot prompt. 2. Strict validation and execution. 3. Narration with chart/table payload. 4. Friendly fallback ("I couldn't understand, try ...") when the LLM fails.

## Acceptance
- 20 sample questions return correct numbers verified against manual SQL. No raw transactions beyond aggregate rows are ever sent to the LLM.
