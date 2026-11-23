"""Unit tests for parity-guard CLI commands."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from parity_guard.cli import main


class TestCLI(unittest.TestCase):
    def test_record_and_verify_cli_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            suite_path = str(Path(tmpdir) / "suite.json")
            report_path = str(Path(tmpdir) / "report.md")

            # 1. Record
            rc_rec = main([
                "record",
                "--cmd", f"{sys.executable} -c \"import sys; sys.stdout.write('cli_ok\\n')\"",
                "--suite", suite_path,
                "--trace-id", "trace_cli_1",
            ])
            self.assertEqual(rc_rec, 0)
            self.assertTrue(Path(suite_path).exists())

            # 2. Audit
            with patch("sys.stdout", new=io.StringIO()) as fake_out:
                rc_audit = main(["audit", "--suite", suite_path])
                self.assertEqual(rc_audit, 0)
                self.assertIn("trace_cli_1", fake_out.getvalue())

            # 3. Verify
            with patch("sys.stdout", new=io.StringIO()) as fake_out:
                rc_ver = main([
                    "verify",
                    "--suite", suite_path,
                    "--cmd", f"{sys.executable} -c \"import sys; sys.stdout.write('cli_ok\\n')\"",
                    "--report", report_path,
                ])
                self.assertEqual(rc_ver, 0)
                self.assertIn("Parity Score:  100.0%", fake_out.getvalue())
            self.assertTrue(Path(report_path).exists())

    def test_diff_cli(self):
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            rc = main([
                "diff",
                "--baseline", f"{sys.executable} -c \"print('sync')\"",
                "--candidate", f"{sys.executable} -c \"print('sync')\"",
            ])
            self.assertEqual(rc, 0)
            self.assertIn("Differential Execution: PASSED", fake_out.getvalue())


if __name__ == "__main__":
    unittest.main()
