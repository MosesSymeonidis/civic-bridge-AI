from collections.abc import AsyncIterator
from uuid import UUID, uuid4

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


async def test_educator_session_and_message_flow(
    client: httpx2.AsyncClient,
) -> None:
    session_response = await client.post(
        "/api/v1/educators/sessions",
        json={
            "country": "Cyprus",
            "region_area": "Nicosia",
            "language": "English",
            "educator_role": "classroom-teacher",
            "learner_age_band": "14-17",
            "education_setting": "secondary-school",
            "support_goal": "classroom-activity",
        },
    )

    assert session_response.status_code == 201
    session = session_response.json()
    UUID(session["session_id"])
    assert session["context"]["educator_role"] == "classroom-teacher"
    assert "without sharing learner names" in session["welcome_message"]

    message_response = await client.post(
        f"/api/v1/educators/sessions/{session['session_id']}/messages",
        json={
            "message": "A harmful statement caused conflict during a lesson."
        },
    )

    assert message_response.status_code == 200
    message = message_response.json()
    assert message["context"] == session["context"]
    assert "secondary school" in message["assistant_message"]
    assert "learners aged 14-17" in message["assistant_message"]
    assert "learning objective" in message["assistant_message"]


async def test_educator_session_rejects_invalid_support_goal(
    client: httpx2.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/educators/sessions",
        json={
            "country": "Cyprus",
            "region_area": "Nicosia",
            "language": "English",
            "educator_role": "classroom-teacher",
            "learner_age_band": "14-17",
            "education_setting": "secondary-school",
            "support_goal": "automatic-punishment",
        },
    )

    assert response.status_code == 422


async def test_educator_message_rejects_unknown_session(
    client: httpx2.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/educators/sessions/00000000-0000-0000-0000-000000000000/messages",
        json={"message": "I need guidance."},
    )

    assert response.status_code == 404


async def test_educator_semantic_classification_is_stored(
    client: httpx2.AsyncClient,
) -> None:
    session_response = await client.post(
        "/api/v1/educators/sessions",
        json={
            "country": "Cyprus",
            "region_area": "Nicosia",
            "language": "English",
            "educator_role": "classroom-teacher",
            "learner_age_band": "14-17",
            "education_setting": "secondary-school",
            "support_goal": "understand-incident",
        },
    )
    session = session_response.json()
    response = await client.post(
        (
            f"/api/v1/educators/sessions/{session['session_id']}"
            "/classifications"
        ),
        json={
            "classification_event_id": str(uuid4()),
            "classification": {
                "topic_id": 22,
                "parent_category": "Anti-LGBTQ Hate",
                "category": "Anti-LGBTQ Political Rhetoric",
                "confidence": 0.72,
                "is_outlier": False,
                "assignment_method": "embedding_cosine_similarity",
                "keywords_role": "topic_description_not_decision_features",
                "keywords": [{"term": "rights", "weight": 0.8}],
                "keywords_topic_id": 22,
                "coordinates": {
                    "x": 6.63,
                    "y": 7.73,
                    "projection_version": "test-projection-v1",
                },
                "nearest_candidate": {
                    "topic_id": 22,
                    "parent_category": "Anti-LGBTQ Hate",
                    "category": "Anti-LGBTQ Political Rhetoric",
                },
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["participant_type"] == "educator"
    assert response.json()["topic_id"] == 22
