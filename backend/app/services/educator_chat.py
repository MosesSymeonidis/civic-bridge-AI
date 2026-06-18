from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.schemas.educator import (
    EducationSetting,
    EducatorContext,
    EducatorRole,
    LearnerAgeBand,
    SupportGoal,
)


@dataclass
class EducatorSession:
    session_id: UUID
    context: EducatorContext
    messages: list[tuple[str, str]] = field(default_factory=list)


class EducatorChatService:
    def __init__(self) -> None:
        self._sessions: dict[UUID, EducatorSession] = {}

    def create_session(self, context: EducatorContext) -> EducatorSession:
        session = EducatorSession(session_id=uuid4(), context=context)
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: UUID) -> EducatorSession | None:
        return self._sessions.get(session_id)

    def reply(self, session: EducatorSession, message: str) -> str:
        session.messages.append(("educator", message))
        response = self._build_response(session.context, message)
        session.messages.append(("assistant", response))
        return response

    @staticmethod
    def welcome_message(context: EducatorContext) -> str:
        age_guidance = {
            LearnerAgeBand.ages_6_9: "developmentally simple and protective",
            LearnerAgeBand.ages_10_13: "clear, scaffolded, and reflective",
            LearnerAgeBand.ages_14_17: "critical, dialogical, and action-oriented",
            LearnerAgeBand.ages_18_plus: "detailed, reflective, and action-oriented",
            LearnerAgeBand.mixed: "adaptable across the learner ages involved",
        }[context.learner_age_band]

        return (
            f"Welcome. I will respond in {context.language} with guidance that is "
            f"{age_guidance}. Describe the incident or educational challenge "
            "without sharing learner names, account details, school identifiers, "
            "or other personal information."
        )

    @staticmethod
    def _build_response(context: EducatorContext, message: str) -> str:
        normalized_message = message.casefold()
        urgent_terms = (
            "immediate danger",
            "weapon",
            "going to hurt",
            "going to kill",
            "credible threat",
        )

        if any(term in normalized_message for term in urgent_terms):
            return (
                "Prioritise immediate safeguarding. Follow your institution's "
                "emergency and child-protection procedures, contact local emergency "
                "services where necessary, preserve evidence, and avoid public "
                "confrontation. This assistant does not replace professional or "
                "statutory safeguarding responsibilities."
            )

        support_prompt = {
            SupportGoal.understand_incident: (
                "Please clarify whether the incident occurred online, in person, "
                "or across both settings, and what language or narrative frame "
                "caused concern."
            ),
            SupportGoal.support_learner: (
                "Please explain the learner's immediate support needs, without "
                "identifying them, and whether your safeguarding process has "
                "already been activated."
            ),
            SupportGoal.classroom_activity: (
                "Please describe the learning objective and available lesson time "
                "so I can suggest an age-appropriate, multiperspective activity."
            ),
            SupportGoal.counter_narrative: (
                "Please describe the harmful narrative and the audience for the "
                "response so we can develop a bridge formulation without repeating "
                "or amplifying the harm."
            ),
            SupportGoal.reporting_next_steps: (
                "Please indicate whether the content is still accessible and what "
                "institutional reporting or evidence-preservation steps have "
                "already been taken."
            ),
        }[context.support_goal]

        role_label = {
            EducatorRole.classroom_teacher: "classroom teacher",
            EducatorRole.school_leader: "school leader",
            EducatorRole.counselor_psychologist: "counsellor or psychologist",
            EducatorRole.youth_worker: "youth worker",
            EducatorRole.teacher_educator: "teacher educator",
            EducatorRole.other: "education professional",
        }[context.educator_role]
        setting_label = {
            EducationSetting.primary_school: "primary school",
            EducationSetting.secondary_school: "secondary school",
            EducationSetting.higher_education: "higher education",
            EducationSetting.vocational_training: "vocational training",
            EducationSetting.non_formal_youth: "non-formal or youth setting",
            EducationSetting.other: "other education setting",
        }[context.education_setting]
        support_label = {
            SupportGoal.understand_incident: "understanding the incident",
            SupportGoal.support_learner: "supporting an affected learner",
            SupportGoal.classroom_activity: "creating a learning activity",
            SupportGoal.counter_narrative: "developing a counter-narrative",
            SupportGoal.reporting_next_steps: "considering reporting steps",
        }[context.support_goal]

        return (
            f"I am using this educator context: {role_label}; {setting_label}; "
            f"learners aged {context.learner_age_band.value}; "
            f"{context.region_area}, {context.country}; language: "
            f"{context.language}; support goal: {support_label}. {support_prompt}"
        )


educator_chat_service = EducatorChatService()
