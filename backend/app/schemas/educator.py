from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EducatorApiModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class LearnerAgeBand(str, Enum):
    ages_6_9 = "6-9"
    ages_10_13 = "10-13"
    ages_14_17 = "14-17"
    ages_18_plus = "18+"
    mixed = "mixed"


class EducatorRole(str, Enum):
    classroom_teacher = "classroom-teacher"
    school_leader = "school-leader"
    counselor_psychologist = "counselor-psychologist"
    youth_worker = "youth-worker"
    teacher_educator = "teacher-educator"
    other = "other"


class EducationSetting(str, Enum):
    primary_school = "primary-school"
    secondary_school = "secondary-school"
    higher_education = "higher-education"
    vocational_training = "vocational-training"
    non_formal_youth = "non-formal-youth"
    other = "other"


class SupportGoal(str, Enum):
    understand_incident = "understand-incident"
    support_learner = "support-learner"
    classroom_activity = "classroom-activity"
    counter_narrative = "counter-narrative"
    reporting_next_steps = "reporting-next-steps"


class EducatorContext(EducatorApiModel):
    country: str = Field(min_length=2, max_length=100)
    region_area: str = Field(min_length=2, max_length=120)
    language: str = Field(min_length=2, max_length=80)
    educator_role: EducatorRole
    learner_age_band: LearnerAgeBand
    education_setting: EducationSetting
    support_goal: SupportGoal


class EducatorSessionCreate(EducatorContext):
    pass


class EducatorSessionResponse(BaseModel):
    session_id: UUID
    context: EducatorContext
    welcome_message: str


class EducatorMessageCreate(EducatorApiModel):
    message: str = Field(min_length=1, max_length=4000)


class EducatorMessageResponse(BaseModel):
    session_id: UUID
    context: EducatorContext
    assistant_message: str
