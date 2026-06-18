from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.analytics import ParticipantType


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: UUID
    participant_type: ParticipantType
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    session_id: UUID
    participant_type: ParticipantType
    assistant_message: str
