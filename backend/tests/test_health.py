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


async def test_health_check(client: httpx2.AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Civic Bridge AI",
        "environment": "development",
    }


async def test_service_info(client: httpx2.AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"
