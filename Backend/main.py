"""
Spend Analyser - FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import chat, insights, reconcile, review, transactions, upload
from app.core.logger import logger
from app.core.setting import settings
from app.src.dao.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Spend Analyser API...")
    init_db()
    logger.info("Database initialised.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Spend Analyser API",
    description="Personal finance tracker: SBI UPI statements + Apple Notes reconciliation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(review.router, prefix="/review", tags=["Review"])
app.include_router(insights.router, prefix="/insights", tags=["Insights"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(reconcile.router, prefix="/reconcile", tags=["Reconcile"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
