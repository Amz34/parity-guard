"""Command-line interface for parity-guard behavioral verification engine."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import List, Optional

from parity_guard.diff import OutputNormalizer
from parity_guard.models import SuiteSummary, TraceRecord
from parity_guard.recorder import SuiteStorage, TraceRecorder
from parity_guard.verifier import ParityVerifier, run_live_differential


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parity-guard",
        description="Behavioral parity verification and differential testing engine for code rewrites.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. record
    p_rec = subparsers.add_parser("record", help="Record golden execution trace from baseline implementation.")
    p_rec.add_argument("--cmd", required=True, help="Command line string to execute (e.g. 'python3 legacy.py')")
    p_rec.add_argument("--trace-id", default="", help="Unique trace identifier (auto-generated if omitted)")
    p_rec.add_argument("--suite", required=True, help="Path to JSON suite file to create or append to")
    p_rec.add_argument("--stdin", default="", help="Optional stdin input string")
    p_rec.add_argument("--tag", action="append", default=[], help="Metadata tag to categorize trace")
    p_rec.add_argument("--timeout", type=float, default=30.0, help="Execution timeout in seconds")

    # 2. verify
    p_ver = subparsers.add_parser("verify", help="Verify candidate implementation against golden traces.")
    p_ver.add_argument("--suite", required=True, help="Path to golden trace suite JSON file")
    p_ver.add_argument("--cmd", required=True, help="Candidate command line string (e.g. './target/release/app')")
    p_ver.add_argument("--threshold", type=float, default=100.0, help="Required passing score (0-100, default: 100)")
    p_ver.add_argument("--report", default="", help="Optional path to write Markdown audit report")
    p_ver.add_argument("--json", action="store_true", help="Output machine-readable JSON to stdout")
    p_ver.add_argument("--strict-stderr", action="store_true", help="Enforce exact stderr matching")
    p_ver.add_argument("--timeout", type=float, default=30.0, help="Per-trace execution timeout in seconds")

    # 3. diff
    p_diff = subparsers.add_parser("diff", help="Run live side-by-side differential test between two commands.")
    p_diff.add_argument("--baseline", required=True, help="Baseline command string (e.g. 'python3 app.py')")
    p_diff.add_argument("--candidate", required=True, help="Candidate command string (e.g. './app_rust')")
    p_diff.add_argument("--stdin", default="", help="Optional stdin input string")
    p_diff.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_diff.add_argument("--timeout", type=float, default=30.0, help="Execution timeout in seconds")

    # 4. audit
    p_audit = subparsers.add_parser("audit", help="Inspect and validate a trace suite file.")
    p_audit.add_argument("--suite", required=True, help="Path to JSON suite file")

    return parser


def handle_record(args: argparse.Namespace) -> int:
    cmd_parts = shlex.split(args.cmd)
    trace_id = args.trace_id or f"trace_{int(Path(args.suite).stat().st_mtime if Path(args.suite).exists() else 0) + 1}"
    recorder = TraceRecorder(timeout=args.timeout)

    trace = recorder.record_execution(
        command=cmd_parts,
        trace_id=trace_id,
        stdin=args.stdin,
        tags=args.tag,
    )

    traces = []
    if Path(args.suite).exists():
        try:
            traces = SuiteStorage.load_suite(args.suite)
        except Exception as e:
            print(f"[warning] Existing suite file invalid or empty, creating new: {e}", file=sys.stderr)

    # Replace existing trace if same id, else append
    traces = [t for t in traces if t.id != trace.id]
    traces.append(trace)
    SuiteStorage.save_suite(args.suite, traces)

    print(f"Recorded trace '{trace.id}': exit_code={trace.exit_code}, duration={trace.duration_ms:.1f}ms, suite={args.suite}")
    return 0


def handle_verify(args: argparse.Namespace) -> int:
    traces = SuiteStorage.load_suite(args.suite)
    candidate_cmd = shlex.split(args.cmd)
    normalizer = OutputNormalizer()
    verifier = ParityVerifier(
        normalizer=normalizer,
        timeout=args.timeout,
        strict_stderr=args.strict_stderr,
    )

    summary = verifier.verify_suite(traces, candidate_cmd)

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(summary.to_markdown(), encoding="utf-8")

    if args.json:
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        print(f"--- Parity Verification Summary ---")
        print(f"Traces Tested: {summary.total_traces}")
        print(f"Passed:        {summary.passed_traces}")
        print(f"Failed:        {summary.failed_traces}")
        print(f"Parity Score:  {summary.parity_score:.1f}%")
        print(f"Threshold:     {args.threshold:.1f}%")

        if summary.failed_traces > 0:
            print("\nFailures:")
            for r in summary.results:
                if not r.passed:
                    print(f"  [FAIL] {r.trace_id} (Score: {r.score:.1f}%)")
                    for d in r.differences:
                        print(f"    - {d.field}: {d.details}")

    is_success = summary.parity_score >= args.threshold and summary.failed_traces == 0
    return 0 if is_success else 1


def handle_diff(args: argparse.Namespace) -> int:
    base_parts = shlex.split(args.baseline)
    cand_parts = shlex.split(args.candidate)

    passed, res = run_live_differential(
        baseline_cmd=base_parts,
        candidate_cmd=cand_parts,
        stdin=args.stdin,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(res.to_dict(), indent=2))
    else:
        status = "PASSED" if passed else "FAILED"
        print(f"Differential Execution: {status} (Score: {res.score:.1f}%)")
        print(f"Duration: {res.duration_ms:.1f}ms")
        if not passed:
            print("Discrepancies:")
            for d in res.differences:
                print(f"  - {d.field}: {d.details}")

    return 0 if passed else 1


def handle_audit(args: argparse.Namespace) -> int:
    traces = SuiteStorage.load_suite(args.suite)
    print(f"Trace Suite Audit: {args.suite}")
    print(f"Total Traces: {len(traces)}")
    for i, t in enumerate(traces, 1):
        tags_str = f" [{', '.join(t.tags)}]" if t.tags else ""
        cmd_str = " ".join(t.command)
        print(f"  {i}. {t.id}: cmd='{cmd_str}', exit={t.exit_code}, stdout_len={len(t.stdout)}{tags_str}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "record":
        return handle_record(args)
    elif args.command == "verify":
        return handle_verify(args)
    elif args.command == "diff":
        return handle_diff(args)
    elif args.command == "audit":
        return handle_audit(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
