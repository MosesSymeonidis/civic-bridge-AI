from fastapi import APIRouter, HTTPException, status

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatSessionNotFoundError, chat_service

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def create_chat_message(request: ChatRequest) -> ChatResponse:
    try:
        return chat_service.reply(request)
    except ChatSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found for the selected participant type.",
        ) from error
