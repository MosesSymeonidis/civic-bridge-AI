from collections.abc import AsyncIterator
from uuid import UUID

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


async def test_student_session_and_message_flow(
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

    assert session_response.status_code == 201
    session = session_response.json()
    UUID(session["session_id"])
    assert session["context"]["region_area"] == "Nicosia"
    assert "clear next-step plan" in session["welcome_message"]
    assert "cannot decide whether a crime happened" in session["welcome_message"]
    assert "do not share names" in session["welcome_message"]

    message_response = await client.post(
        f"/api/v1/students/sessions/{session['session_id']}/messages",
        json={"message": "Someone posted a hateful comment about me."},
    )

    assert message_response.status_code == 200
    message = message_response.json()
    assert message["context"] == session["context"]
    assert "Nicosia, Cyprus" in message["assistant_message"]
    assert "age band: 14-17" in message["assistant_message"]


async def test_student_session_rejects_invalid_age_band(
    client: httpx2.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/students/sessions",
        json={
            "country": "Cyprus",
            "region_area": "Nicosia",
            "language": "English",
            "age_band": "under-6",
        },
    )

    assert response.status_code == 422


async def test_student_session_rejects_whitespace_only_context(
    client: httpx2.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/students/sessions",
        json={
            "country": "  ",
            "region_area": "Nicosia",
            "language": "English",
            "age_band": "14-17",
        },
    )

    assert response.status_code == 422


async def test_student_message_rejects_unknown_session(
    client: httpx2.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/students/sessions/00000000-0000-0000-0000-000000000000/messages",
        json={"message": "I need help."},
    )

    assert response.status_code == 404
