"""
SQLAlchemy models for Spend Analyser
All money columns use Numeric(12,2) – never float.
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ─── Source file (dedupe uploads) ────────────────────────────────────────────

class SourceFile(Base):
    __tablename__ = "source_file"

    id = Column(Integer, primary_key=True)
    kind = Column(String(20), nullable=False)          # bank_pdf | notes
    file_hash = Column(String(64), unique=True, nullable=False)
    period = Column(String(7), nullable=False)          # YYYY-MM
    original_name = Column(String(255))
    ingested_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="source_file")
    parse_errors = relationship("ParseError", back_populates="source_file")
    note_lines = relationship("NoteLine", back_populates="source_file")


# ─── Category (seeded, user-editable sub-cats) ───────────────────────────────

class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)     # Emoji or icon name
    parent_id = Column(Integer, ForeignKey("category.id"), nullable=True)

    parent = relationship("Category", remote_side="Category.id", backref="children")
    transactions = relationship("Transaction", back_populates="category")
    merchants = relationship("Merchant", back_populates="default_category")
    rules = relationship("Rule", back_populates="category")
    note_lines = relationship("NoteLine", back_populates="category")
    budgets = relationship("Budget", back_populates="category")


# ─── Merchant ─────────────────────────────────────────────────────────────────

class Merchant(Base):
    __tablename__ = "merchant"

    id = Column(Integer, primary_key=True)
    canonical_name = Column(String(200), unique=True, nullable=False)
    aliases_json = Column(Text, default="[]")    # JSON list of strings
    default_category_id = Column(Integer, ForeignKey("category.id"), nullable=True)
    is_person = Column(Boolean, default=False)

    default_category = relationship("Category", back_populates="merchants")
    transactions = relationship("Transaction", back_populates="merchant")

    @property
    def aliases(self) -> list[str]:
        return json.loads(self.aliases_json or "[]")

    @aliases.setter
    def aliases(self, value: list[str]):
        self.aliases_json = json.dumps(value)


# ─── Transaction ─────────────────────────────────────────────────────────────

class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True)
    txn_hash = Column(String(64), unique=True, nullable=False)
    txn_date = Column(String(10), nullable=False)       # ISO date string
    amount = Column(Numeric(12, 2), nullable=False)
    direction = Column(String(6), nullable=False)       # debit | credit
    raw_narration = Column(Text)
    upi_ref = Column(String(50))
    upi_handle = Column(String(100))
    payee_raw = Column(String(200))
    merchant_id = Column(Integer, ForeignKey("merchant.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=True)
    confidence = Column(Numeric(4, 3), default=0.0)
    status = Column(String(20), default="pending")      # auto | confirmed | pending
    cat_source = Column(String(20))                     # rule | merchant | llm | none
    source_file_id = Column(Integer, ForeignKey("source_file.id"), nullable=False)

    source_file = relationship("SourceFile", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    note_lines = relationship("NoteLine", back_populates="matched_txn")
    review_items = relationship("ReviewItem", back_populates="txn")

    __table_args__ = (
        Index("ix_txn_date", "txn_date"),
        Index("ix_txn_category", "category_id"),
        Index("ix_txn_merchant", "merchant_id"),
        Index("ix_txn_status", "status"),
    )


# ─── Rule ────────────────────────────────────────────────────────────────────

class Rule(Base):
    __tablename__ = "rule"

    id = Column(Integer, primary_key=True)
    match_type = Column(String(20), nullable=False)     # payee | merchant | regex | amount_range
    pattern = Column(String(500), nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    priority = Column(Integer, default=10)
    created_from = Column(String(10), default="user")   # user | llm

    category = relationship("Category", back_populates="rules")


# ─── Note line ───────────────────────────────────────────────────────────────

class NoteLine(Base):
    __tablename__ = "note_line"

    id = Column(Integer, primary_key=True)
    period = Column(String(7), nullable=False)           # YYYY-MM
    item_text = Column(String(300), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=True)
    matched_txn_id = Column(Integer, ForeignKey("transaction.id"), nullable=True)
    match_score = Column(Numeric(4, 3), default=0.0)
    source_file_id = Column(Integer, ForeignKey("source_file.id"), nullable=True)

    category = relationship("Category", back_populates="note_lines")
    matched_txn = relationship("Transaction", back_populates="note_lines")
    source_file = relationship("SourceFile", back_populates="note_lines")
    review_items = relationship("ReviewItem", back_populates="note_line")

    __table_args__ = (Index("ix_note_period", "period"),)


# ─── Review item ─────────────────────────────────────────────────────────────

class ReviewItem(Base):
    __tablename__ = "review_item"

    id = Column(Integer, primary_key=True)
    kind = Column(String(30), nullable=False)
    # unknown_payee | low_conf | unmatched_note | unmatched_txn | amount_gap | category_conflict
    txn_id = Column(Integer, ForeignKey("transaction.id"), nullable=True)
    note_line_id = Column(Integer, ForeignKey("note_line.id"), nullable=True)
    question = Column(Text, nullable=False)
    options_json = Column(Text, default="[]")            # JSON list of {label, value}
    status = Column(String(10), default="open")          # open | resolved | skipped
    resolved_at = Column(DateTime, nullable=True)
    resolution_json = Column(Text, nullable=True)        # store applied resolution

    txn = relationship("Transaction", back_populates="review_items")
    note_line = relationship("NoteLine", back_populates="review_items")

    __table_args__ = (Index("ix_review_status", "status"),)


# ─── Budget ──────────────────────────────────────────────────────────────────

class Budget(Base):
    __tablename__ = "budget"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)
    monthly_amount = Column(Numeric(12, 2), nullable=False)
    effective_from = Column(String(7), nullable=False)   # YYYY-MM

    category = relationship("Category", back_populates="budgets")


# ─── Parse error ─────────────────────────────────────────────────────────────

class ParseError(Base):
    __tablename__ = "parse_error"

    id = Column(Integer, primary_key=True)
    source_file_id = Column(Integer, ForeignKey("source_file.id"), nullable=True)
    page = Column(Integer, nullable=True)
    raw_text = Column(Text)
    reason = Column(Text)
    occurred_at = Column(DateTime, default=datetime.utcnow)

    source_file = relationship("SourceFile", back_populates="parse_errors")


# ─── LLM usage ───────────────────────────────────────────────────────────────

class LlmUsage(Base):
    __tablename__ = "llm_usage"

    id = Column(Integer, primary_key=True)
    provider = Column(String(50), nullable=False)
    date = Column(String(10), nullable=False)            # YYYY-MM-DD
    calls = Column(Integer, default=0)
    failures = Column(Integer, default=0)
