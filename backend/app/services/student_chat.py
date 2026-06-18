from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.schemas.student import AgeBand, StudentContext


@dataclass
class StudentSession:
    session_id: UUID
    context: StudentContext
    messages: list[tuple[str, str]] = field(default_factory=list)


class StudentChatService:
    def __init__(self) -> None:
        self._sessions: dict[UUID, StudentSession] = {}

    def create_session(self, context: StudentContext) -> StudentSession:
        session = StudentSession(session_id=uuid4(), context=context)
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: UUID) -> StudentSession | None:
        return self._sessions.get(session_id)

    def reply(self, session: StudentSession, message: str) -> str:
        session.messages.append(("student", message))
        response = self._build_response(session.context, message)
        session.messages.append(("assistant", response))
        return response

    @staticmethod
    def welcome_message(context: StudentContext) -> str:
        age_intro = {
            AgeBand.ages_6_9: "I will use simple, clear language.",
            AgeBand.ages_10_13: "I will explain things clearly and step by step.",
            AgeBand.ages_14_17: "I will help you examine what happened and consider your options.",
            AgeBand.ages_18_plus: "I will help you examine the incident and consider constructive next steps.",
        }[context.age_band]

        return (
            f"Hi. I am ready to listen in {context.language}. {age_intro} "
            "You can ask a question or describe what happened, and I will help "
            "you understand it and build a clear next-step plan. I cannot decide "
            "whether a crime happened or punish anyone. Please do not share names, "
            "account details, addresses, or other identifying information."
        )

    @staticmethod
    def _build_response(context: StudentContext, message: str) -> str:
        normalized_message = message.casefold()
        urgent_terms = (
            "immediate danger",
            "going to hurt",
            "going to kill",
            "weapon",
            "threatened me now",
        )

        if any(term in normalized_message for term in urgent_terms):
            return (
                "Your safety comes first. If anyone may be in immediate danger, "
                "contact local emergency services or a trusted adult nearby now. "
                "Preserve evidence if it is safe to do so, and do not confront the "
                "person publicly. You can continue here after you are safe."
            )

        age_prompt = {
            AgeBand.ages_6_9: (
                "Thank you for telling me. What happened was not your fault. "
                "Can you tell me whether this happened online or in person, and "
                "whether a trusted adult already knows?"
            ),
            AgeBand.ages_10_13: (
                "Thank you for explaining what happened. Was this online or in "
                "person, and what would help most right now: understanding the "
                "message, finding support, or deciding how to respond?"
            ),
            AgeBand.ages_14_17: (
                "Thank you for describing the incident. To understand the context, "
                "was it online or in person, and what would help most: analysing the "
                "harmful message, preserving evidence, seeking support, or preparing "
                "a constructive response?"
            ),
            AgeBand.ages_18_plus: (
                "Thank you for describing the incident. To understand the context, "
                "was it online or in person, and what outcome are you seeking: "
                "analysis, support or reporting guidance, evidence preservation, "
                "or a constructive response?"
            ),
        }[context.age_band]

        return (
            f"I am considering the context you provided: {context.region_area}, "
            f"{context.country}; language: {context.language}; age band: "
            f"{context.age_band.value}. {age_prompt}"
        )


student_chat_service = StudentChatService()
