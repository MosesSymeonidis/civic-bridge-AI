from collections.abc import AsyncIterator

import httpx2
import pytest

from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[httpx2.AsyncClient]:
    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


async def test_chat_dispatches_student_message(
    client: httpx2.AsyncClient,
) -> None:
    session_response = await client.post(
        "/api/v1/students/sessions",
        json={
            "country": "Cyprus",
            "region_area": "Nicosia",
            "language": "English",
            "age_band": "14-17",
        },
    )
    session_id = session_response.json()["session_id"]

    response = await client.post(
        "/api/v1/chat",
        json={
            "session_id": session_id,
            "participant_type": "student",
            "message": "Someone posted a harmful comment.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["participant_type"] == "student"
    assert "Nicosia, Cyprus" in body["assistant_message"]


async def test_chat_dispatches_educator_message(
    client: httpx2.AsyncClient,
) -> None:
    session_response = await client.post(
        "/api/v1/educators/sessions",
        json={
            "country": "Cyprus",
            "region_area": "Limassol",
            "language": "English",
            "educator_role": "classroom-teacher",
            "learner_age_band": "10-13",
            "education_setting": "secondary-school",
            "support_goal": "support-learner",
        },
    )
    session_id = session_response.json()["session_id"]

    response = await client.post(
        "/api/v1/chat",
        json={
            "session_id": session_id,
            "participant_type": "educator",
            "message": "A learner needs support after an incident.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["participant_type"] == "educator"
    assert "secondary school" in body["assistant_message"]


async def test_chat_rejects_session_for_wrong_participant_type(
    client: httpx2.AsyncClient,
) -> None:
    session_response = await client.post(
        "/api/v1/students/sessions",
        json={
            "country": "Cyprus",
            "region_area": "Nicosia",
            "language": "English",
            "age_band": "14-17",
        },
    )

    response = await client.post(
        "/api/v1/chat",
        json={
            "session_id": session_response.json()["session_id"],
            "participant_type": "educator",
            "message": "This role does not match the session.",
        },
    )

    assert response.status_code == 404


async def test_chat_rejects_whitespace_only_message(
    client: httpx2.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/chat",
        json={
            "session_id": "00000000-0000-0000-0000-000000000000",
            "participant_type": "student",
            "message": "   ",
        },
    )

    assert response.status_code == 422
