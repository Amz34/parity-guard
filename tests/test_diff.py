"""Unit tests for diff and normalization logic."""

import unittest
from parity_guard.diff import (
    OutputNormalizer,
    compare_json_objects,
    compute_similarity_ratio,
    compute_string_diff,
)


class TestDiffEngine(unittest.TestCase):
    def test_normalizer_masks_uuid_and_timestamp(self):
        normalizer = OutputNormalizer()
        raw = "User 123e4567-e89b-12d3-a456-426614174000 logged at 2026-11-23T11:22:33Z in /tmp/scratch_file.txt"
        normalized = normalizer.normalize(raw)
        self.assertNotIn("123e4567-e89b-12d3-a456-426614174000", normalized)
        self.assertNotIn("2026-11-23T11:22:33Z", normalized)
        self.assertIn("[UUID_MASKED]", normalized)
        self.assertIn("[TIMESTAMP_MASKED]", normalized)
        self.assertIn("[TMPDIR]/masked_path", normalized)

    def test_compare_json_identical(self):
        exp = {"status": "ok", "items": [1, 2, 3], "nested": {"val": 42.0}}
        act = {"nested": {"val": 42.0000001}, "status": "ok", "items": [1, 2, 3]}
        diffs = compare_json_objects(exp, act)
        self.assertEqual(len(diffs), 0)

    def test_compare_json_mismatches(self):
        exp = {"status": "ok", "count": 10, "items": ["a"]}
        act = {"status": "error", "items": ["a", "b"]}
        diffs = compare_json_objects(exp, act)
        fields = [d.field for d in diffs]
        self.assertIn("json:$.status", fields)
        self.assertIn("json:$.count", fields)
        self.assertIn("json:$.items", fields)

    def test_compute_string_diff(self):
        diff = compute_string_diff("alpha\nbeta\n", "alpha\ngamma\n")
        self.assertIn("-beta", diff)
        self.assertIn("+gamma", diff)

    def test_compute_similarity_ratio(self):
        self.assertEqual(compute_similarity_ratio("hello world", "hello world"), 1.0)
        self.assertGreater(compute_similarity_ratio("hello world", "hello work"), 0.8)


if __name__ == "__main__":
    unittest.main()
