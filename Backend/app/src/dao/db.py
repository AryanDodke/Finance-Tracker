"""
Database engine, session factory, and init_db
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.logger import logger
from app.core.setting import settings
from app.src.models.db_models import Base, Category

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite only
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from typing import Annotated

from fastapi import Depends

SessionDep = Annotated[Session, Depends(get_session)]


# ─── Seed data ───────────────────────────────────────────────────────────────

SEED_CATEGORIES = [
    # (name, parent_name, icon)
    ("Personal", None, "face-personal"),
    ("Rent", "Personal", "face-rent"),
    ("Food", "Personal", "face-food"),
    ("Travel", "Personal", "face-travel"),
    ("Home Expense", None, "face-home"),
    ("Outing", "Personal", "face-outing"),
    # System
    ("Transfer", None, "face-transfer"),
    ("Income", None, "face-income"),
    ("Uncategorised", None, "face-unknown"),
]

SEMANTIC_DICTIONARY = [
    # (pattern, category_name)
    ("zomato", "Food"),
    ("swiggy", "Food"),
    ("uber", "Travel"),
    ("ola", "Travel"),
    ("blinkit", "Food"),
    ("zepto", "Food"),
    ("amazon", "Home Expense"),
    ("flipkart", "Home Expense"),
    ("salary", "Income"),
    ("dmart", "Home Expense"),
    ("makemytrip", "Travel"),
    ("bookmyshow", "Outing"),
    ("netflix", "Personal"),
    ("spotify", "Personal"),
]

def seed_categories(session: Session) -> None:
    """Idempotent: insert categories that don't exist yet, update icons."""
    existing = {c.name: c for c in session.query(Category).all()}

    for name, parent_name, icon in SEED_CATEGORIES:
        if name not in existing:
            parent = existing.get(parent_name) if parent_name else None
            cat = Category(name=name, icon=icon, parent_id=parent.id if parent else None)
            session.add(cat)
            session.flush()
            existing[name] = cat
        elif existing[name].icon != icon:
            existing[name].icon = icon

    session.commit()
    logger.info(f"Categories seeded: {len(existing)} total.")

def seed_semantic_dictionary(session: Session) -> None:
    """Idempotent: insert default categorization rules."""
    from app.src.models.db_models import Rule
    
    existing_rules = {r.pattern.lower(): r for r in session.query(Rule).filter_by(created_from="system").all()}
    categories = {c.name: c for c in session.query(Category).all()}
    
    added = 0
    for pattern, cat_name in SEMANTIC_DICTIONARY:
        if pattern.lower() not in existing_rules and cat_name in categories:
            cat_id = categories[cat_name].id
            rule = Rule(
                match_type="payee",
                pattern=pattern,
                category_id=cat_id,
                priority=100,
                created_from="system"
            )
            session.add(rule)
            added += 1
            
    if added > 0:
        session.commit()
        logger.info(f"Seeded {added} semantic rules.")


def init_db() -> None:
    """Create tables and seed categories. Idempotent."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_categories(session)
        seed_semantic_dictionary(session)
    logger.info("DB initialised.")
