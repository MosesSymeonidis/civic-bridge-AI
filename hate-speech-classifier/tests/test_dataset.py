import unittest

from hate_speech_clustering.dataset import (
    UNDECIDED,
    consensus_label,
    consensus_targets,
    normalize_post,
)


class DatasetTest(unittest.TestCase):
    def test_consensus_label_returns_majority(self):
        label, votes = consensus_label(["hatespeech", "normal", "hatespeech"])

        self.assertEqual(label, "hatespeech")
        self.assertEqual(votes, {"hatespeech": 2, "normal": 1})

    def test_consensus_label_marks_three_way_split_undecided(self):
        label, votes = consensus_label(["hatespeech", "normal", "offensive"])

        self.assertEqual(label, UNDECIDED)
        self.assertEqual(
            votes, {"hatespeech": 1, "normal": 1, "offensive": 1}
        )

    def test_consensus_targets_are_multilabel_and_ignore_none(self):
        annotations = [
            {"target": ["Women", "Islam"]},
            {"target": ["Women", "None"]},
            {"target": ["Women", "Islam", "Islam"]},
        ]

        targets, votes = consensus_targets(annotations)

        self.assertEqual(targets, ["Islam", "Women"])
        self.assertEqual(votes, {"Islam": 2, "Women": 3})

    def test_normalize_post_preserves_votes_and_split(self):
        post = {
            "post_tokens": ["example", "text"],
            "annotators": [
                {"label": "normal", "target": ["None"]},
                {"label": "normal", "target": ["None"]},
                {"label": "offensive", "target": ["Other"]},
            ],
            "rationales": [[0, 0], [0, 0], [1, 0]],
        }

        record = normalize_post("post-1", post, {"post-1": "train"})

        self.assertEqual(record["text"], "example text")
        self.assertEqual(record["split"], "train")
        self.assertEqual(record["content_label"], "normal")
        self.assertEqual(record["target_labels"], [])
        self.assertEqual(record["target_votes"], {"Other": 1})


if __name__ == "__main__":
    unittest.main()

