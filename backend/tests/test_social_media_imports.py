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


def _import_payload(post_id: str) -> dict:
    return {
        "post_id": post_id,
        "country": "Cyprus",
        "region_area": "Nicosia",
        "language": "English",
        "platform": "x",
        "published_at": "2026-06-14T09:30:00Z",
        "source_reference": "batch-2026-06",
        "incident_text": "[PERSON_1] is targeted.",
        "analysis": {
            "tier": 3,
            "tier_label": "Potential hate speech",
            "rationale": [
                {
                    "citation_id": "policy-1",
                    "reason": "The post targets a protected group.",
                }
            ],
            "barriers": [
                {
                    "id": "stigma",
                    "span": "[PERSON_1] is targeted.",
                    "rationale": "A degrading group label is applied.",
                    "promoters": ["outgroup_empathy"],
                }
            ],
            "target_group": "A protected group",
            "themes": ["Religious Hatred"],
            "confidence": "high",
            "related_cases": [],
        },
        "classification": {
            "topic_id": 2,
            "parent_category": "Anti-Muslim and Anti-Arab Hate",
            "category": "Anti-Muslim Ideology and Rights Rhetoric",
            "confidence": 0.72,
            "is_outlier": False,
            "assignment_method": "embedding_cosine_similarity",
            "keywords_role": "topic_description_not_decision_features",
            "keywords": [{"term": "rights", "weight": 0.8}],
            "keywords_topic_id": 2,
            "coordinates": {
                "x": 2.2,
                "y": 6.3,
                "projection_version": "test-projection-v1",
            },
            "nearest_candidate": {
                "topic_id": 2,
                "parent_category": "Anti-Muslim and Anti-Arab Hate",
                "category": "Anti-Muslim Ideology and Rights Rhetoric",
            },
        },
    }


async def test_social_media_import_is_atomic_deduplicated_and_aggregated(
    client: httpx2.AsyncClient,
) -> None:
    check_before = await client.post(
        "/api/v1/imports/social-media/check",
        json={"post_ids": ["post-001"]},
    )
    first = await client.post(
        "/api/v1/imports/social-media/events",
        json=_import_payload("post-001"),
    )
    retry = await client.post(
        "/api/v1/imports/social-media/events",
        json=_import_payload("post-001"),
    )
    check_after = await client.post(
        "/api/v1/imports/social-media/check",
        json={"post_ids": ["post-001", "post-002"]},
    )

    assert check_before.status_code == 200
    assert check_before.json() == {"existing_post_ids": []}
    assert first.status_code == 201
    assert first.json()["status"] == "imported"
    assert retry.status_code == 201
    assert retry.json()["status"] == "duplicate"
    assert retry.json()["discussion_analysis_id"] == (
        first.json()["discussion_analysis_id"]
    )
    assert check_after.json() == {"existing_post_ids": ["post-001"]}

    dashboard_response = await client.get(
        "/api/v1/dashboard/summary",
        params={"minimum_group_size": 1},
    )
    dashboard = dashboard_response.json()
    assert dashboard["totals"]["analysed_conversations"] == 1
    assert dashboard["totals"]["pending_reviews"] == 1
    assert dashboard["sources"] == [
        {
            "key": "social-media",
            "label": "Social media posts",
            "count": 1,
            "percentage": 100.0,
        }
    ]
    assert sum(point["social_media"] for point in dashboard["trend"]) == 1
    assert dashboard["semantic_clusters"]["total_points"] == 1
    assert dashboard["semantic_clusters"]["points"][0]["incident_text"] == (
        "[PERSON_1] is targeted."
    )

    reviews_response = await client.get("/api/v1/dashboard/reviews")
    review = reviews_response.json()["items"][0]
    assert review["participant_type"] == "social-media"
    assert review["target_group"] == "A protected group"
    assert review["incident_text"] == "[PERSON_1] is targeted."


async def test_social_media_import_rejects_raw_post_text(
    client: httpx2.AsyncClient,
) -> None:
    payload = _import_payload("post-raw")
    payload["post_text"] = "This content must never reach backend storage."

    response = await client.post(
        "/api/v1/imports/social-media/events",
        json=payload,
    )

    assert response.status_code == 422
