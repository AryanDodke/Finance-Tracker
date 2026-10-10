"""Upload router: PDF statements and notes text."""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_422_UNPROCESSABLE_ENTITY

from app.src.dao.db import SessionDep
from app.src.dto.schemas import IngestResult, NotesIngestResult
from app.src.services.ingestion import ingest_statement

router = APIRouter()


@router.post("/statement", response_model=IngestResult)
async def upload_statement(
    session: SessionDep,
    file: UploadFile = File(...),
    password: str = Form(...),
    period: str = Form(...),   # YYYY-MM
):
    """Upload a password-protected SBI UPI statement PDF."""
    if file.filename and "." in file.filename and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Only PDF files are accepted.")
    if not period or len(period) != 7:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Period must be in YYYY-MM format.")

    file_bytes = await file.read()
    try:
        result = await ingest_statement(session, file_bytes, file.filename, password, period)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return IngestResult(
        source_file_id=result.source_file_id,
        period=result.period,
        inserted=result.inserted,
        skipped=result.skipped,
        errors=result.errors,
        message=result.message,
    )


@router.post("/notes", response_model=NotesIngestResult)
async def upload_notes(
    session: SessionDep,
    text: str = Form(...),
    period: str = Form(...),
):
    """Upload a month's Apple Notes spending breakdown as plain text."""
    if not period or len(period) != 7:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Period must be in YYYY-MM format.")

    import hashlib

    from app.src.models.db_models import SourceFile

    file_hash = hashlib.sha256(f"{period}:{text}".encode()).hexdigest()
    existing = session.query(SourceFile).filter_by(file_hash=file_hash).first()
    if existing:
        return NotesIngestResult(
            source_file_id=existing.id,
            period=period,
            lines_parsed=0,
            message="Already ingested.",
        )

    source_file = SourceFile(kind="notes", file_hash=file_hash, period=period)
    session.add(source_file)
    session.flush()

    from app.src.services.notes_parser import ingest_notes
    lines_parsed = ingest_notes(session, text, period, source_file.id)

    # Trigger reconciliation
    try:
        from app.src.services.reconciler import reconcile_period
        reconcile_period(session, period)
    except Exception:
        pass  # reconciliation is best-effort

    return NotesIngestResult(
        source_file_id=source_file.id,
        period=period,
        lines_parsed=lines_parsed,
        message=f"Parsed {lines_parsed} note lines for {period}.",
    )
