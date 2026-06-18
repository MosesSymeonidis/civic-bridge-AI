import unittest


class FakeService:
    projection_version = "test-projection-v1"

    def predict(self, text):
        return {
            "text": text.strip(),
            "topic_id": 2,
            "parent_category": "Anti-Muslim and Anti-Arab Hate",
            "category": "Anti-Muslim Ideology and Rights Rhetoric",
            "confidence": 0.67,
            "is_outlier": False,
            "assignment_method": "embedding_cosine_similarity",
            "keywords_role": "topic_description_not_decision_features",
            "keywords": [
                {"term": "muslim", "weight": 0.9},
                {"term": "islam", "weight": 0.7},
            ],
            "keywords_topic_id": 2,
            "coordinates": {
                "x": 1.25,
                "y": -0.75,
                "projection_version": self.projection_version,
            },
            "nearest_candidate": {
                "topic_id": 2,
                "parent_category": "Anti-Muslim and Anti-Arab Hate",
                "category": "Anti-Muslim Ideology and Rights Rhetoric",
            },
        }


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        try:
            import httpx
            from hate_speech_clustering.api import create_app
        except ImportError as exc:
            raise unittest.SkipTest(f"FastAPI test dependencies missing: {exc}")

        self.app = create_app(service_factory=FakeService)
        self.lifespan = self.app.router.lifespan_context(self.app)
        await self.lifespan.__aenter__()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.lifespan.__aexit__(None, None, None)

    async def test_health(self):
        response = await self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "projection_version": "test-projection-v1",
            },
        )

    async def test_predict(self):
        response = await self.client.post(
            "/predict",
            json={"text": "Example sentence"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["topic_id"], 2)
        self.assertEqual(
            payload["parent_category"],
            "Anti-Muslim and Anti-Arab Hate",
        )
        self.assertEqual(payload["coordinates"]["x"], 1.25)
        self.assertEqual(payload["keywords"][0]["term"], "muslim")

    async def test_rejects_empty_text(self):
        response = await self.client.post("/predict", json={"text": ""})

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
