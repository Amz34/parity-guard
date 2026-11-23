"""Unit tests for trace recording and suite storage."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from parity_guard.models import TraceRecord
from parity_guard.recorder import SuiteStorage, TraceRecorder


class TestRecorder(unittest.TestCase):
    def test_record_simple_command(self):
        recorder = TraceRecorder(timeout=5.0)
        trace = recorder.record_execution(
            command=[sys.executable, "-c", "import sys; sys.stdout.write('parity_ok\\n'); sys.exit(0)"],
            trace_id="test_rec_1",
            tags=["smoke"],
        )
        self.assertEqual(trace.id, "test_rec_1")
        self.assertEqual(trace.exit_code, 0)
        self.assertIn("parity_ok", trace.stdout)
        self.assertEqual(trace.tags, ["smoke"])
        self.assertGreaterEqual(trace.duration_ms, 0.0)

    def test_record_stdin_and_env(self):
        recorder = TraceRecorder(timeout=5.0)
        cmd = [sys.executable, "-c", "import os, sys; sys.stdout.write(os.environ.get('MY_KEY', '') + ':' + sys.stdin.read())"]
        trace = recorder.record_execution(
            command=cmd,
            trace_id="test_stdin",
            stdin="input_payload",
            env={"MY_KEY": "secret_val"},
        )
        self.assertEqual(trace.stdout, "secret_val:input_payload")
        self.assertEqual(trace.exit_code, 0)

    def test_suite_storage_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_file = str(Path(tmpdir) / "suite.json")
            traces = [
                TraceRecord(id="t1", command=["cmd1"], stdout="out1"),
                TraceRecord(id="t2", command=["cmd2"], stdout="out2"),
            ]
            SuiteStorage.save_suite(suite_file, traces, metadata={"author": "test"})

            loaded = SuiteStorage.load_suite(suite_file)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].id, "t1")
            self.assertEqual(loaded[1].stdout, "out2")


if __name__ == "__main__":
    unittest.main()
