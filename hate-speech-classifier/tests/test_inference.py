import unittest
from unittest.mock import patch

from hate_speech_clustering.inference import TopicClusterer


class FakeTopicInfo:
    def itertuples(self):
        return [
            type(
                "Row",
                (),
                {
                    "Topic": -1,
                    "Name": "-1_mixed",
                    "CustomName": "Mixed or Unclustered",
                },
            )(),
            type(
                "Row",
                (),
                {
                    "Topic": 2,
                    "Name": "2_exclude_community",
                    "CustomName": "Exclusion Rhetoric",
                },
            )(),
        ]


class FakeModel:
    def get_topic_info(self):
        return FakeTopicInfo()

    def get_topic(self, topic):
        return [("exclude", 0.8), ("community", 0.5)] if topic == 2 else []

    def transform(self, texts):
        topics = [2 for _ in texts]
        probabilities = [0.8 if "strong" in text else 0.1 for text in texts]
        return topics, probabilities


class FakeBERTopic:
    @staticmethod
    def load(path, embedding_model=None):
        return FakeModel()


class InferenceTest(unittest.TestCase):
    def make_clusterer(self, min_confidence=0.25):
        with patch.dict(
            "sys.modules",
            {"bertopic": type("Module", (), {"BERTopic": FakeBERTopic})()},
        ):
            return TopicClusterer("model", min_confidence=min_confidence)

    def test_accepts_assignment_above_threshold(self):
        prediction = self.make_clusterer().predict("strong match")

        self.assertEqual(prediction.topic, 2)
        self.assertFalse(prediction.is_outlier)
        self.assertEqual(prediction.label, "Exclusion Rhetoric")
        self.assertEqual(prediction.candidate_label, "Exclusion Rhetoric")
        self.assertIsNone(prediction.group)
        self.assertIsNone(prediction.candidate_group)
        self.assertEqual(prediction.generated_label, "2_exclude_community")
        self.assertEqual(prediction.top_words, ["exclude", "community"])

    def test_rejects_assignment_below_threshold(self):
        prediction = self.make_clusterer().predict("weak match")

        self.assertEqual(prediction.topic, -1)
        self.assertEqual(prediction.candidate_topic, 2)
        self.assertTrue(prediction.is_outlier)
        self.assertEqual(prediction.label, "Mixed or Unclustered")
        self.assertEqual(prediction.candidate_label, "Exclusion Rhetoric")

    def test_always_assign_disables_threshold(self):
        prediction = self.make_clusterer(min_confidence=None).predict("weak match")

        self.assertEqual(prediction.topic, 2)
        self.assertFalse(prediction.is_outlier)

    def test_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            self.make_clusterer().predict(" ")


if __name__ == "__main__":
    unittest.main()
