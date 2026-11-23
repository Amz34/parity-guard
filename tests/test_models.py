"""Unit tests for parity_guard data models."""

import unittest
from parity_guard.models import (
    ParityDifference,
    SuiteSummary,
    TraceRecord,
    VerificationResult,
)


class TestModels(unittest.TestCase):
    def test_trace_record_roundtrip(self):
        record = TraceRecord(
            id="trace_001",
            command=["echo", "hello"],
            stdin="",
            stdout="hello\n",
            stderr="",
            exit_code=0,
            duration_ms=4.2,
            env={"FOO": "bar"},
            tags=["cli", "basic"],
            metadata={"source": "test"},
        )
        d = record.to_dict()
        reconstructed = TraceRecord.from_dict(d)
        self.assertEqual(record.id, reconstructed.id)
        self.assertEqual(record.command, reconstructed.command)
        self.assertEqual(record.stdout, reconstructed.stdout)
        self.assertEqual(record.exit_code, reconstructed.exit_code)
        self.assertEqual(record.tags, ["cli", "basic"])

    def test_suite_summary_markdown(self):
        res1 = VerificationResult(
            trace_id="test_1",
            command=["app", "--help"],
            passed=True,
            score=100.0,
            differences=[],
            duration_ms=5.0,
            candidate_stdout="help",
            candidate_stderr="",
            candidate_exit_code=0,
        )
        res2 = VerificationResult(
            trace_id="test_2",
            command=["app", "--bad"],
            passed=False,
            score=50.0,
            differences=[
                ParityDifference(field="exit_code", expected=1, actual=2, details="bad code")
            ],
            duration_ms=6.0,
            candidate_stdout="",
            candidate_stderr="err",
            candidate_exit_code=2,
        )
        summary = SuiteSummary(
            total_traces=2,
            passed_traces=1,
            failed_traces=1,
            parity_score=75.0,
            results=[res1, res2],
        )
        md = summary.to_markdown()
        self.assertIn("# Parity Verification Audit Report", md)
        self.assertIn("**Total Traces:** 2", md)
        self.assertIn("**Passed:** 1", md)
        self.assertIn("`test_1`", md)
        self.assertIn("PASS", md)
        self.assertIn("FAIL", md)


if __name__ == "__main__":
    unittest.main()
