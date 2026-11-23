"""Unit tests for parity verification and differential testing."""

import sys
import unittest
from parity_guard.models import TraceRecord
from parity_guard.verifier import ParityVerifier, run_live_differential


class TestVerifier(unittest.TestCase):
    def test_verify_identical_execution(self):
        verifier = ParityVerifier()
        trace = TraceRecord(
            id="t1",
            command=[sys.executable, "-c", "print('hello')"],
            stdout="hello\n",
            exit_code=0,
        )
        res = verifier.verify_single(trace, [sys.executable, "-c", "print('hello')"])
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 100.0)
        self.assertEqual(len(res.differences), 0)

    def test_verify_exit_code_mismatch(self):
        verifier = ParityVerifier()
        trace = TraceRecord(
            id="t2",
            command=[sys.executable, "-c", "import sys; sys.exit(0)"],
            stdout="",
            exit_code=0,
        )
        res = verifier.verify_single(trace, [sys.executable, "-c", "import sys; sys.exit(1)"])
        self.assertFalse(res.passed)
        self.assertLess(res.score, 100.0)
        self.assertTrue(any(d.field == "exit_code" for d in res.differences))

    def test_verify_suite_aggregation(self):
        verifier = ParityVerifier()
        traces = [
            TraceRecord(id="t1", command=[sys.executable, "-c", "print('1')"], stdout="1\n", exit_code=0),
            TraceRecord(id="t2", command=[sys.executable, "-c", "print('2')"], stdout="2\n", exit_code=0),
        ]
        summary = verifier.verify_suite(traces, [sys.executable, "-c", "import sys; print(sys.argv[1])"])
        self.assertEqual(summary.total_traces, 2)
        # Note: arg passing test
        self.assertEqual(len(summary.results), 2)

    def test_live_differential(self):
        base_cmd = [sys.executable, "-c", "print('parity_test')"]
        cand_cmd = [sys.executable, "-c", "print('parity_test')"]
        passed, res = run_live_differential(base_cmd, cand_cmd)
        self.assertTrue(passed)
        self.assertEqual(res.score, 100.0)


if __name__ == "__main__":
    unittest.main()
