"""
Pydantic schemas for the Spend Analyser API.
All amounts are Decimal strings in the API.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel

# ─── Source file ──────────────────────────────────────────────────────────────

class IngestResult(BaseModel):
    source_file_id: int
    period: str
    inserted: int
    skipped: int
    errors: int
    message: str


class NotesIngestResult(BaseModel):
    source_file_id: int
    period: str
    lines_parsed: int
    message: str


# ─── Category ─────────────────────────────────────────────────────────────────

class CategoryOut(BaseModel):
    id: int
    name: str
    icon: str | None = None
    parent_id: int | None = None

    model_config = {"from_attributes": True}


# ─── Transaction ──────────────────────────────────────────────────────────────

class TxnOut(BaseModel):
    id: int
    txn_hash: str
    txn_date: str
    amount: Decimal
    direction: str
    raw_narration: str | None = None
    payee_raw: str | None = None
    upi_ref: str | None = None
    upi_handle: str | None = None
    merchant_id: int | None = None
    merchant_name: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    confidence: Decimal | None = None
    status: str
    cat_source: str | None = None

    model_config = {"from_attributes": True}


class TxnPatch(BaseModel):
    category_id: int
    apply_scope: str = "this_only"   # this_only | all_past | all_past_and_future
    create_rule: bool = False


class TxnListParams(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    category_id: int | None = None
    merchant_id: int | None = None
    status: str | None = None
    direction: str | None = None
    page: int = 1
    page_size: int = 50


# ─── Merchant ─────────────────────────────────────────────────────────────────

class MerchantOut(BaseModel):
    id: int
    canonical_name: str
    aliases: list[str]
    default_category_id: int | None = None
    is_person: bool

    model_config = {"from_attributes": True}


# ─── Rule ─────────────────────────────────────────────────────────────────────

class RuleIn(BaseModel):
    match_type: str   # payee | merchant | regex | amount_range
    pattern: str
    category_id: int
    priority: int = 10


class RuleOut(BaseModel):
    id: int
    match_type: str
    pattern: str
    category_id: int
    priority: int
    created_from: str

    model_config = {"from_attributes": True}


# ─── Review ───────────────────────────────────────────────────────────────────

class ReviewOption(BaseModel):
    label: str
    value: Any


class ReviewItemOut(BaseModel):
    id: int
    kind: str
    txn_id: int | None = None
    note_line_id: int | None = None
    question: str
    options: list[ReviewOption]
    status: str
    # enriched
    txn: TxnOut | None = None

    model_config = {"from_attributes": True}


class ReviewGroup(BaseModel):
    payee: str
    count: int
    items: list[ReviewItemOut]


class ResolveAnswer(BaseModel):
    category_id: int | None = None
    skip: bool = False
    note: str | None = None


class ResolveResult(BaseModel):
    resolved: int
    rules_created: int
    txns_updated: int


class BulkResolveIn(BaseModel):
    item_ids: list[int]
    answer: ResolveAnswer
    apply_scope: str = "this_only"


# ─── Insights ─────────────────────────────────────────────────────────────────

class MonthCategoryTotal(BaseModel):
    period: str
    category_id: int
    category_name: str
    total: Decimal


class MoMChange(BaseModel):
    category_id: int
    category_name: str
    current: Decimal
    previous: Decimal
    change_pct: float | None = None


class MerchantSpend(BaseModel):
    merchant_id: int
    merchant_name: str
    total: Decimal
    txn_count: int


class RecurringCharge(BaseModel):
    merchant_id: int
    merchant_name: str
    typical_amount: Decimal
    last_date: str
    frequency_days: int


class Anomaly(BaseModel):
    txn_id: int
    txn_date: str
    merchant_name: str | None
    amount: Decimal
    category_name: str
    z_score: float


class BudgetStatus(BaseModel):
    category_id: int
    category_name: str
    budget: Decimal
    actual: Decimal
    remaining: Decimal
    pct_used: float


class InsightsSummary(BaseModel):
    period: str
    category_totals: list[MonthCategoryTotal]
    mom_changes: list[MoMChange]
    top_merchants: list[MerchantSpend]
    recurring: list[RecurringCharge]
    anomalies: list[Anomaly]
    budget_status: list[BudgetStatus]
    savings_rate: float | None = None
    review_count: int


# ─── Budget ───────────────────────────────────────────────────────────────────

class BudgetIn(BaseModel):
    category_id: int
    monthly_amount: Decimal
    effective_from: str   # YYYY-MM


class BudgetOut(BaseModel):
    id: int
    category_id: int
    category_name: str | None = None
    monthly_amount: Decimal
    effective_from: str

    model_config = {"from_attributes": True}


# ─── Reconcile ───────────────────────────────────────────────────────────────

class ReconcileLineMatch(BaseModel):
    note_id: int
    note_item: str
    note_amount: Decimal
    txn_id: int | None = None
    txn_date: str | None = None
    txn_amount: Decimal | None = None
    merchant_name: str | None = None
    match_score: float


class ReconcileCategoryGap(BaseModel):
    category_name: str
    noted_total: Decimal
    bank_total: Decimal
    gap: Decimal
    gap_pct: float


class ReconcileReport(BaseModel):
    period: str
    matched: list[ReconcileLineMatch]
    unmatched_notes: list[ReconcileLineMatch]
    unmatched_txns: list[TxnOut]
    category_gaps: list[ReconcileCategoryGap]


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatQuestion(BaseModel):
    question: str


class ChatAnswer(BaseModel):
    question: str
    answer: str
    data: Any | None = None   # table or chart data
    chart_type: str | None = None
