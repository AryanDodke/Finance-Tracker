# 09 Insights Engine

## Purpose
Compute spending insights from confirmed, categorised bank data (and notes accuracy).

## Files
- `services/insights.py`
- `services/budgets.py`
- `routers/insights.py`: `GET /insights/summary`, `GET/PUT /budgets`.

## Function definitions
```python
def monthly_totals(session: Session, start: str, end: str) -> list[MonthCategoryTotal]: ...
def mom_change(session: Session, period: str) -> list[Change]: ...
def rolling_average(session: Session, category_id: int, months: int = 3) -> Decimal: ...
def top_merchants(session: Session, period: str, limit: int = 10) -> list[MerchantSpend]: ...
def detect_recurring(session: Session) -> list[RecurringCharge]: ...         # same merchant, similar amount, 25-35 day gap
def detect_anomalies(session: Session, period: str, z: float = 3.0) -> list[Anomaly]: ...
def weekday_hour_pattern(session: Session) -> PatternMatrix: ...
def savings_rate(session: Session, period: str) -> Decimal | None: ...      # needs income
def budget_vs_actual(session: Session, period: str) -> list[BudgetStatus]: ...
def notes_accuracy(session: Session, period: str) -> list[AccuracyScore]: ... # from 07 gaps
def build_summary(session: Session, period: str) -> InsightsSummary: ...    # aggregate for API
```

## Rules
Exclude `Transfer` and pending-status rows by default (toggle). Credits count as `Income` only if categorised so.

## Communication
- Reads: `transaction`, `category`, `budget`, `note_line`, `07` totals.
- Called by: `routers/insights.py`, `10.qa` (data source).
- Read by: `11.frontend` Dashboard.

## Tasks
1. SQL-first aggregations (indexed). 2. Recurring and anomaly detection with tests on synthetic data. 3. Budget CRUD. 4. Plain-language insight strings ("Food up 22% vs 3-month avg").

## Acceptance
- Totals per month equal the sum of the transaction rows. Seeded subscription is detected. Seeded outlier is flagged.
