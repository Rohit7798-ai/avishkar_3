"""
API endpoints for Farm AI Copilot Chat.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat & AI Assistant"])


@router.post("", response_model=ChatResponse)
def chat_with_farm_copilot(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Conversational agricultural assistant endpoint.
    Translates farmer queries into grounded explanations and actionable decisions.
    """
    service = ChatService(db)
    return service.process_chat(request)
