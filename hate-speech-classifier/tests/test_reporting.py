import unittest

from hate_speech_clustering.reporting import (
    content_label_rows,
    target_label_rows,
)


class ReportingTest(unittest.TestCase):
    def setUp(self):
        self.records = [
            {"content_label": "hatespeech", "target_labels": ["Women", "Islam"]},
            {"content_label": "offensive", "target_labels": ["Women"]},
            {"content_label": "hatespeech", "target_labels": []},
        ]
        self.topics = [0, 0, -1]

    def test_content_rows_use_within_topic_share(self):
        rows = content_label_rows(self.records, self.topics)

        self.assertIn(
            {
                "topic": 0,
                "content_label": "hatespeech",
                "count": 1,
                "topic_share": 0.5,
            },
            rows,
        )

    def test_target_rows_count_each_document_once(self):
        rows = target_label_rows(self.records, self.topics)

        self.assertIn(
            {
                "topic": 0,
                "target_label": "Women",
                "document_count": 2,
                "topic_document_share": 1.0,
            },
            rows,
        )
        self.assertIn(
            {
                "topic": -1,
                "target_label": "__no_consensus_target__",
                "document_count": 1,
                "topic_document_share": 1.0,
            },
            rows,
        )


if __name__ == "__main__":
    unittest.main()
