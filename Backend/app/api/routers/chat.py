"""Chat router."""
from fastapi import APIRouter

from app.src.dao.db import SessionDep
from app.src.dto.schemas import ChatAnswer, ChatQuestion
from app.src.services.qa import ask

router = APIRouter()


@router.post("", response_model=ChatAnswer)
def chat(body: ChatQuestion, session: SessionDep):
    """Answer a natural-language question about spending."""
    result = ask(session, body.question)
    return ChatAnswer(
        question=result["question"],
        answer=result["answer"],
        data=result.get("data"),
        chart_type=result.get("chart_type"),
    )
