from app.domain.analytics import ParticipantType
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.educator_chat import educator_chat_service
from app.services.student_chat import student_chat_service


class ChatSessionNotFoundError(Exception):
    pass


class ChatService:
    def reply(self, request: ChatRequest) -> ChatResponse:
        if request.participant_type == ParticipantType.student:
            session = student_chat_service.get_session(request.session_id)
            if session is None:
                raise ChatSessionNotFoundError
            assistant_message = student_chat_service.reply(
                session,
                request.message,
            )
        else:
            session = educator_chat_service.get_session(request.session_id)
            if session is None:
                raise ChatSessionNotFoundError
            assistant_message = educator_chat_service.reply(
                session,
                request.message,
            )

        return ChatResponse(
            session_id=request.session_id,
            participant_type=request.participant_type,
            assistant_message=assistant_message,
        )


chat_service = ChatService()
