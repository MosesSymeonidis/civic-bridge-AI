from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudentApiModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class AgeBand(str, Enum):
    ages_6_9 = "6-9"
    ages_10_13 = "10-13"
    ages_14_17 = "14-17"
    ages_18_plus = "18+"


class StudentContext(StudentApiModel):
    country: str = Field(min_length=2, max_length=100)
    region_area: str = Field(min_length=2, max_length=120)
    language: str = Field(min_length=2, max_length=80)
    age_band: AgeBand


class StudentSessionCreate(StudentContext):
    pass


class StudentSessionResponse(BaseModel):
    session_id: UUID
    context: StudentContext
    welcome_message: str


class StudentMessageCreate(StudentApiModel):
    message: str = Field(min_length=1, max_length=4000)


class StudentMessageResponse(BaseModel):
    session_id: UUID
    context: StudentContext
    assistant_message: str
