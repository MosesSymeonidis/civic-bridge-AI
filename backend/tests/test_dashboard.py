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


async def _create_student_session(
    client: httpx2.AsyncClient,
) -> dict:
    response = await client.post(
        "/api/v1/students/sessions",
        json={
            "country": "Cyprus",
            "region_area": "Nicosia",
            "language": "English",
            "age_band": "14-17",
        },
    )
    assert response.status_code == 201
    return response.json()


async def _create_educator_session(
    client: httpx2.AsyncClient,
) -> dict:
    response = await client.post(
        "/api/v1/educators/sessions",
        json={
            "country": "Cyprus",
            "region_area": "Limassol",
            "language": "Greek",
            "educator_role": "classroom-teacher",
            "learner_age_band": "10-13",
            "education_setting": "secondary-school",
            "support_goal": "support-learner",
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_empty_database_returns_empty_dashboard(
    client: httpx2.AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/dashboard/summary",
        params={"time_range": "30d", "minimum_group_size": 1},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"

    dashboard = response.json()
    assert dashboard["totals"] == {
        "analysed_conversations": 0,
        "incident_signals": 0,
        "human_review_rate": 0.0,
        "pending_reviews": 0,
        "completed_reviews": 0,
        "review_completion_rate": 0.0,
        "constructive_response_rate": 0.0,
        "previous_period_change": None,
    }
    assert dashboard["regions"] == []
    assert dashboard["sources"] == []
    assert dashboard["severity"] == []
    assert dashboard["semantic_barriers"] == []
    assert dashboard["bridge_promoters"] == []
    assert dashboard["age_bands"] == []
    assert dashboard["languages"] == []
    assert dashboard["reviewer_outcomes"] == []
    assert all(point["total"] == 0 for point in dashboard["trend"])
    assert dashboard["semantic_clusters"] == {
        "projection_version": None,
        "total_points": 0,
        "displayed_points": 0,
        "categories": [],
        "points": [],
    }


async def test_completed_discussions_feed_dashboard_aggregates(
    client: httpx2.AsyncClient,
) -> None:
    student = await _create_student_session(client)
    message_response = await client.post(
        f"/api/v1/students/sessions/{student['session_id']}/messages",
        json={"message": "A harmful statement was posted online."},
    )
    assert message_response.status_code == 200

    student_completion = await client.post(
        f"/api/v1/students/sessions/{student['session_id']}/complete",
        json={
            "severity": "potential-hate-speech",
            "semantic_barriers": ["stigma", "collective-blame"],
            "bridge_promoters": ["outgroup-empathy"],
            "reviewer_outcome": "bridge-response-adapted",
        },
    )
    assert student_completion.status_code == 201
    completed_student = student_completion.json()
    UUID(completed_student["id"])
    assert completed_student["participant_type"] == "student"
    assert completed_student["incident_detected"] is True
    assert completed_student["human_review_required"] is True
    assert completed_student["constructive_response"] is True
    assert completed_student["message_count"] == 1

    educator = await _create_educator_session(client)
    educator_completion = await client.post(
        f"/api/v1/educators/sessions/{educator['session_id']}/complete",
        json={
            "severity": "ordinary-political-expression",
            "semantic_barriers": [],
            "bridge_promoters": ["corroboration"],
            "constructive_response": False,
        },
    )
    assert educator_completion.status_code == 201

    response = await client.get(
        "/api/v1/dashboard/summary",
        params={"time_range": "30d", "minimum_group_size": 1},
    )
    assert response.status_code == 200
    dashboard = response.json()

    assert dashboard["totals"] == {
        "analysed_conversations": 2,
        "incident_signals": 1,
        "human_review_rate": 50.0,
        "pending_reviews": 0,
        "completed_reviews": 1,
        "review_completion_rate": 100.0,
        "constructive_response_rate": 50.0,
        "previous_period_change": None,
    }
    assert dashboard["period"]["bucket"] == "week"
    assert sum(point["total"] for point in dashboard["trend"]) == 1

    source_counts = {
        item["key"]: item["count"] for item in dashboard["sources"]
    }
    assert source_counts == {"student": 1, "educator": 1}

    region_counts = {
        item["key"]: item["count"] for item in dashboard["regions"]
    }
    assert region_counts == {"Nicosia": 1}

    severity_counts = {
        item["key"]: item["count"] for item in dashboard["severity"]
    }
    assert severity_counts == {
        "ordinary-political-expression": 1,
        "potential-hate-speech": 1,
    }

    reviewed_response = await client.get(
        "/api/v1/dashboard/reviews",
        params={"reviewed": "true"},
    )
    assert reviewed_response.status_code == 200
    assert reviewed_response.json()["items"][0]["incident_text"] == (
        "A harmful statement was posted online."
    )

    barrier_counts = {
        item["key"]: item["count"]
        for item in dashboard["semantic_barriers"]
    }
    assert barrier_counts == {"stigma": 1, "collective-blame": 1}

    filtered_response = await client.get(
        "/api/v1/dashboard/summary",
        params={
            "time_range": "30d",
            "participant_type": "student",
            "language": "English",
            "minimum_group_size": 1,
        },
    )
    assert filtered_response.status_code == 200
    assert (
        filtered_response.json()["totals"]["analysed_conversations"] == 1
    )

    profile_response = await client.get(
        "/api/v1/dashboard/summary",
        params={
            "time_range": "30d",
            "country": "Cyprus",
            "region_area": "Nicosia",
            "severity": "potential-hate-speech",
            "minimum_group_size": 1,
        },
    )
    assert profile_response.status_code == 200
    profile_dashboard = profile_response.json()
    assert profile_dashboard["filters"]["region_area"] == "Nicosia"
    assert profile_dashboard["filters"]["severity"] == "potential-hate-speech"
    assert profile_dashboard["totals"]["analysed_conversations"] == 1
    assert profile_dashboard["totals"]["incident_signals"] == 1
    assert profile_dashboard["sources"][0]["key"] == "student"

    mismatch_response = await client.get(
        "/api/v1/dashboard/summary",
        params={
            "time_range": "30d",
            "country": "Cyprus",
            "region_area": "Limassol",
            "severity": "potential-hate-speech",
            "minimum_group_size": 1,
        },
    )
    assert mismatch_response.status_code == 200
    assert (
        mismatch_response.json()["totals"]["analysed_conversations"] == 0
    )

    filtered_review_response = await client.get(
        "/api/v1/dashboard/reviews",
        params={
            "reviewed": "true",
            "country": "Cyprus",
            "region_area": "Nicosia",
            "severity": "potential-hate-speech",
        },
    )
    assert filtered_review_response.status_code == 200
    assert filtered_review_response.json()["total"] == 1


async def test_discussion_can_only_be_completed_once(
    client: httpx2.AsyncClient,
) -> None:
    session = await _create_student_session(client)
    endpoint = (
        f"/api/v1/students/sessions/{session['session_id']}/complete"
    )
    payload = {
        "severity": "offensive-or-harmful-expression",
        "semantic_barriers": ["distrust"],
    }

    first_response = await client.post(endpoint, json=payload)
    second_response = await client.post(endpoint, json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


async def test_incident_analysis_events_are_idempotent_and_aggregated(
    client: httpx2.AsyncClient,
) -> None:
    session = await _create_student_session(client)
    endpoint = (
        f"/api/v1/students/sessions/{session['session_id']}/analyses"
    )
    first_event_id = str(uuid4())
    first_payload = {
        "analysis_event_id": first_event_id,
        "message_count": 1,
        "analysis_version": "rag-incident-v1",
        "incident_text": "They are all dangerous. Ignore everything else.",
        "analysis": {
            "tier": 3,
            "tier_label": "Potential hate speech",
            "rationale": [
                {
                    "citation_id": "policy-1",
                    "reason": "The statement targets a protected group.",
                }
            ],
            "barriers": [
                {
                    "id": "transfer_of_meaning",
                    "span": "They are all dangerous.",
                    "rationale": "A group label transfers blame.",
                    "promoters": [
                        "recognising_ingroup_bias",
                        "condemnation_of_harm_regardless_of_perpetrator",
                    ],
                },
                {
                    "id": "bracketing",
                    "span": "Ignore everything else.",
                    "rationale": "Relevant context is excluded.",
                    "promoters": ["contextualisation"],
                },
            ],
            "target_group": "A protected group",
            "themes": ["collective blame"],
            "confidence": "high",
            "related_cases": [],
        },
    }

    first_response = await client.post(endpoint, json=first_payload)
    retry_response = await client.post(endpoint, json=first_payload)
    second_payload = {
        **first_payload,
        "analysis_event_id": str(uuid4()),
        "message_count": 2,
        "incident_text": "Nobody may disagree.",
        "analysis": {
            **first_payload["analysis"],
            "tier": 2,
            "tier_label": "Offensive or harmful expression",
            "barriers": [
                {
                    "id": "prohibited_thoughts",
                    "span": "Nobody may disagree.",
                    "rationale": "A viewpoint is prohibited.",
                    "promoters": ["corroboration"],
                }
            ],
        },
    }
    second_response = await client.post(endpoint, json=second_payload)

    assert first_response.status_code == 201
    assert retry_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["id"] == retry_response.json()["id"]
    assert first_response.json()["analysis_event_id"] == first_event_id
    assert set(first_response.json()["semantic_barriers"]) == {
        "transfer-of-meaning",
        "bracketing",
    }
    assert set(first_response.json()["bridge_promoters"]) == {
        "ingroup-bias-recognition",
        "condemnation-of-harm-regardless-of-perpetrator",
        "contextualisation",
    }

    dashboard_response = await client.get(
        "/api/v1/dashboard/summary",
        params={"time_range": "30d", "minimum_group_size": 1},
    )
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["totals"]["analysed_conversations"] == 2
    assert dashboard["totals"]["incident_signals"] == 2

    severity_counts = {
        item["key"]: item["count"] for item in dashboard["severity"]
    }
    assert severity_counts == {
        "offensive-or-harmful-expression": 1,
        "potential-hate-speech": 1,
    }


async def test_one_event_updates_every_applicable_dashboard_aggregate(
    client: httpx2.AsyncClient,
) -> None:
    session = await _create_student_session(client)
    event_id = str(uuid4())
    analysis_response = await client.post(
        f"/api/v1/students/sessions/{session['session_id']}/analyses",
        json={
            "analysis_event_id": event_id,
            "message_count": 1,
            "analysis_version": "rag-incident-v1",
            "incident_text": "A stigmatising statement.",
            "analysis": {
                "tier": 3,
                "tier_label": "Potential hate speech",
                "rationale": [],
                "barriers": [
                    {
                        "id": "stigma",
                        "span": "A stigmatising statement.",
                        "rationale": "A protected group is denigrated.",
                        "promoters": [
                            "outgroup_empathy",
                            "condemnation_of_harm_regardless_of_perpetrator",
                        ],
                    }
                ],
                "target_group": "A protected group",
                "themes": ["stigma"],
                "confidence": "high",
                "related_cases": [],
            },
        },
    )
    classification_response = await client.post(
        f"/api/v1/students/sessions/{session['session_id']}/classifications",
        json={
            "classification_event_id": event_id,
            "classification_version": "semantic-cluster-api-v1",
            "classification": {
                "topic_id": 2,
                "parent_category": "Anti-Muslim and Anti-Arab Hate",
                "category": "Anti-Muslim Ideology and Rights Rhetoric",
                "confidence": 0.72,
                "is_outlier": False,
                "assignment_method": "embedding_cosine_similarity",
                "keywords_role": "topic_description_not_decision_features",
                "keywords": [{"term": "stigma", "weight": 0.8}],
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
        },
    )

    assert analysis_response.status_code == 201
    assert classification_response.status_code == 201

    response = await client.get(
        "/api/v1/dashboard/summary",
        params={"time_range": "30d"},
    )
    assert response.status_code == 200
    dashboard = response.json()

    assert dashboard["filters"]["minimum_group_size"] == 1
    assert dashboard["totals"] == {
        "analysed_conversations": 1,
        "incident_signals": 1,
        "human_review_rate": 100.0,
        "pending_reviews": 1,
        "completed_reviews": 0,
        "review_completion_rate": 0.0,
        "constructive_response_rate": 0.0,
        "previous_period_change": None,
    }
    assert dashboard["regions"][0]["key"] == "Nicosia"
    assert dashboard["sources"][0]["key"] == "student"
    assert dashboard["severity"][0]["key"] == "potential-hate-speech"
    assert dashboard["semantic_barriers"][0]["key"] == "stigma"
    assert {
        item["key"] for item in dashboard["bridge_promoters"]
    } == {
        "outgroup-empathy",
        "condemnation-of-harm-regardless-of-perpetrator",
    }
    assert dashboard["age_bands"][0]["key"] == "14-17"
    assert dashboard["languages"][0]["key"] == "English"
    assert sum(point["total"] for point in dashboard["trend"]) == 1
    assert dashboard["reviewer_outcomes"] == []
    assert dashboard["semantic_clusters"]["total_points"] == 1
    assert dashboard["semantic_clusters"]["displayed_points"] == 1


async def test_reviewer_can_process_pending_incident(
    client: httpx2.AsyncClient,
) -> None:
    session = await _create_student_session(client)
    event_id = str(uuid4())
    analysis_response = await client.post(
        f"/api/v1/students/sessions/{session['session_id']}/analyses",
        json={
            "analysis_event_id": event_id,
            "message_count": 2,
            "incident_text": (
                "An anonymized statement targeting a protected group."
            ),
            "analysis": {
                "tier": 3,
                "tier_label": "Potential hate speech",
                "rationale": [
                    {
                        "citation_id": "policy-1",
                        "reason": "The statement targets a protected group.",
                    }
                ],
                "barriers": [
                    {
                        "id": "stigma",
                        "span": "Raw source text is not returned to reviewers.",
                        "rationale": "The statement applies a degrading label.",
                        "promoters": ["outgroup_empathy"],
                    }
                ],
                "target_group": "A protected group",
                "themes": ["stigma", "religious hatred"],
                "confidence": "high",
                "related_cases": [],
            },
        },
    )
    assert analysis_response.status_code == 201
    incident_id = analysis_response.json()["id"]

    pending_response = await client.get(
        "/api/v1/dashboard/reviews",
        params={"time_range": "30d", "country": "Cyprus"},
    )
    assert pending_response.status_code == 200
    assert pending_response.headers["cache-control"] == "no-store"
    pending = pending_response.json()
    assert pending["total"] == 1
    assert pending["items"][0]["id"] == incident_id
    assert pending["items"][0]["target_group"] == "A protected group"
    assert pending["items"][0]["themes"] == [
        "stigma",
        "religious hatred",
    ]
    assert pending["items"][0]["incident_text"] == (
        "An anonymized statement targeting a protected group."
    )
    assert pending["items"][0]["rationale"][0]["citation_id"] == "policy-1"
    assert pending["items"][0]["barriers"] == [
        {
            "id": "stigma",
            "rationale": "The statement applies a degrading label.",
            "promoters": ["outgroup_empathy"],
        }
    ]
    assert "span" not in pending["items"][0]["barriers"][0]
    assert pending["items"][0]["reviewed_at"] is None

    review_response = await client.patch(
        f"/api/v1/dashboard/reviews/{incident_id}",
        json={
            "reviewer_reference": "reviewer-17",
            "notes": "Use the proposed bridge response in follow-up.",
        },
    )
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["reviewed_at"] is not None
    assert review["reviewer_reference"] == "reviewer-17"
    assert review["reviewer_outcome"] is None
    assert review["constructive_response"] is False

    pending_after = await client.get("/api/v1/dashboard/reviews")
    reviewed_after = await client.get(
        "/api/v1/dashboard/reviews",
        params={"reviewed": "true"},
    )
    assert pending_after.json()["total"] == 0
    assert reviewed_after.json()["total"] == 1
    assert reviewed_after.json()["items"][0]["id"] == incident_id

    dashboard_response = await client.get(
        "/api/v1/dashboard/summary",
        params={"minimum_group_size": 1},
    )
    dashboard = dashboard_response.json()
    assert dashboard["totals"]["pending_reviews"] == 0
    assert dashboard["totals"]["completed_reviews"] == 1
    assert dashboard["totals"]["review_completion_rate"] == 100.0
    assert dashboard["totals"]["constructive_response_rate"] == 0.0
    assert dashboard["reviewer_outcomes"] == []


async def test_review_endpoint_rejects_incident_not_requiring_review(
    client: httpx2.AsyncClient,
) -> None:
    session = await _create_student_session(client)
    completion_response = await client.post(
        f"/api/v1/students/sessions/{session['session_id']}/complete",
        json={"severity": "ordinary-political-expression"},
    )

    response = await client.patch(
        f"/api/v1/dashboard/reviews/{completion_response.json()['id']}",
        json={
            "reviewer_reference": "reviewer-17",
            "outcome": "educational-activity-created",
        },
    )

    assert response.status_code == 409


async def test_completion_rejects_duplicate_analytical_labels(
    client: httpx2.AsyncClient,
) -> None:
    session = await _create_student_session(client)
    response = await client.post(
        f"/api/v1/students/sessions/{session['session_id']}/complete",
        json={
            "severity": "offensive-or-harmful-expression",
            "semantic_barriers": ["stigma", "stigma"],
        },
    )

    assert response.status_code == 422


async def test_semantic_classifications_are_idempotent_and_feed_scatterplot(
    client: httpx2.AsyncClient,
) -> None:
    session = await _create_student_session(client)
    endpoint = (
        f"/api/v1/students/sessions/{session['session_id']}/classifications"
    )
    event_id = str(uuid4())
    payload = {
        "classification_event_id": event_id,
        "classification_version": "semantic-cluster-api-v1",
        "classification": {
            "topic_id": 18,
            "parent_category": "Anti-Immigrant and Refugee Hate",
            "category": "Anti-Muslim Refugee Exclusion",
            "confidence": 0.61,
            "is_outlier": False,
            "assignment_method": "embedding_cosine_similarity",
            "keywords_role": "topic_description_not_decision_features",
            "keywords": [
                {"term": "refugee", "weight": 0.9},
                {"term": "exclude", "weight": 0.7},
            ],
            "keywords_topic_id": 18,
            "coordinates": {
                "x": 2.65,
                "y": 7.75,
                "projection_version": "test-projection-v1",
            },
            "nearest_candidate": {
                "topic_id": 18,
                "parent_category": "Anti-Immigrant and Refugee Hate",
                "category": "Anti-Muslim Refugee Exclusion",
            },
        },
    }

    first_response = await client.post(endpoint, json=payload)
    retry_response = await client.post(endpoint, json=payload)

    assert first_response.status_code == 201
    assert retry_response.status_code == 201
    assert first_response.json()["id"] == retry_response.json()["id"]
    assert first_response.json()["classification_event_id"] == event_id

    dashboard_response = await client.get(
        "/api/v1/dashboard/summary",
        params={"time_range": "30d", "minimum_group_size": 1},
    )
    assert dashboard_response.status_code == 200
    plot = dashboard_response.json()["semantic_clusters"]
    assert plot["projection_version"] == "test-projection-v1"
    assert plot["total_points"] == 1
    assert plot["displayed_points"] == 1
    assert plot["categories"] == [
        {
            "topic_id": 18,
            "parent_category": "Anti-Immigrant and Refugee Hate",
            "category": "Anti-Muslim Refugee Exclusion",
            "count": 1,
            "keywords": ["refugee", "exclude"],
        }
    ]
    assert plot["points"] == [
        {
            "x": 2.65,
            "y": 7.75,
            "topic_id": 18,
            "parent_category": "Anti-Immigrant and Refugee Hate",
            "category": "Anti-Muslim Refugee Exclusion",
            "confidence": 0.61,
            "is_outlier": False,
            "keywords": ["refugee", "exclude"],
            "participant_type": "student",
            "incident_text": None,
        }
    ]

    private_dashboard_response = await client.get(
        "/api/v1/dashboard/summary",
        params={"time_range": "30d", "minimum_group_size": 2},
    )
    assert private_dashboard_response.status_code == 200
    private_plot = private_dashboard_response.json()["semantic_clusters"]
    assert private_plot["total_points"] == 1
    assert private_plot["displayed_points"] == 0
    assert private_plot["points"] == []


async def test_semantic_classification_rejects_raw_message_text(
    client: httpx2.AsyncClient,
) -> None:
    session = await _create_student_session(client)
    response = await client.post(
        f"/api/v1/students/sessions/{session['session_id']}/classifications",
        json={
            "classification_event_id": str(uuid4()),
            "classification": {
                "text": "This must not enter backend analytics.",
                "topic_id": -1,
                "parent_category": None,
                "category": None,
                "confidence": 0.1,
                "is_outlier": True,
                "assignment_method": "embedding_cosine_similarity",
                "keywords_role": "topic_description_not_decision_features",
                "keywords": [],
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
        },
    )

    assert response.status_code == 422
