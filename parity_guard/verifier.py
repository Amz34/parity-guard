"""Verification and differential oracle engine for parity-guard."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from typing import Callable, Dict, List, Optional, Tuple

from parity_guard.diff import (
    OutputNormalizer,
    compare_json_objects,
    compute_similarity_ratio,
    compute_string_diff,
)
from parity_guard.models import (
    ParityDifference,
    SuiteSummary,
    TraceRecord,
    VerificationResult,
)


class ParityVerifier:
    """Replays candidate implementations against golden traces and verifies behavioral parity."""

    def __init__(
        self,
        normalizer: Optional[OutputNormalizer] = None,
        working_dir: Optional[str] = None,
        timeout: float = 30.0,
        strict_exit_code: bool = True,
        strict_stderr: bool = False,
    ):
        self.normalizer = normalizer or OutputNormalizer()
        self.working_dir = working_dir or os.getcwd()
        self.timeout = timeout
        self.strict_exit_code = strict_exit_code
        self.strict_stderr = strict_stderr

    def _build_candidate_cmd(self, candidate_cmd_prefix: List[str], trace_cmd: List[str]) -> List[str]:
        """Construct the candidate execution command by replacing the baseline executable."""
        # If trace_cmd has arguments after the executable (index 1:), append them to candidate prefix
        args = trace_cmd[1:] if len(trace_cmd) > 1 else []
        return list(candidate_cmd_prefix) + args

    def verify_single(
        self,
        trace: TraceRecord,
        candidate_cmd: List[str],
    ) -> VerificationResult:
        """Execute candidate against a single golden trace and evaluate discrepancies."""
        full_cmd = self._build_candidate_cmd(candidate_cmd, trace.command)
        merged_env = os.environ.copy()
        merged_env.update(trace.env)

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                full_cmd,
                input=trace.stdin,
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                env=merged_env,
                timeout=self.timeout,
            )
            duration_ms = (time.perf_counter() - start) * 1000.0
            act_stdout = proc.stdout
            act_stderr = proc.stderr
            act_exit_code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            act_stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            act_stderr = (exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")) + "\n[TIMED_OUT]"
            act_exit_code = -9

        differences: List[ParityDifference] = []

        # 1. Exit code check
        if trace.exit_code != act_exit_code:
            differences.append(
                ParityDifference(
                    field="exit_code",
                    expected=trace.exit_code,
                    actual=act_exit_code,
                    details=f"Exit code mismatch: expected {trace.exit_code}, got {act_exit_code}",
                    severity="error",
                )
            )

        # 2. Normalize outputs
        norm_exp_stdout = self.normalizer.normalize(trace.stdout)
        norm_act_stdout = self.normalizer.normalize(act_stdout)
        norm_exp_stderr = self.normalizer.normalize(trace.stderr)
        norm_act_stderr = self.normalizer.normalize(act_stderr)

        # 3. Check for JSON stdout structure
        is_json_match = False
        try:
            exp_json = json.loads(norm_exp_stdout)
            act_json = json.loads(norm_act_stdout)
            json_diffs = compare_json_objects(exp_json, act_json)
            if json_diffs:
                differences.extend(json_diffs)
            is_json_match = True
        except (ValueError, TypeError):
            # Not JSON, fall back to textual diff
            pass

        if not is_json_match:
            if norm_exp_stdout != norm_act_stdout:
                diff_text = compute_string_diff(norm_exp_stdout, norm_act_stdout)
                differences.append(
                    ParityDifference(
                        field="stdout",
                        expected=norm_exp_stdout[:200],
                        actual=norm_act_stdout[:200],
                        details=diff_text[:1000] if diff_text else "Textual mismatch in stdout",
                        severity="error",
                    )
                )

        # 4. Check stderr if required
        if self.strict_stderr and norm_exp_stderr != norm_act_stderr:
            diff_text = compute_string_diff(norm_exp_stderr, norm_act_stderr, label_exp="exp_err", label_act="act_err")
            differences.append(
                ParityDifference(
                    field="stderr",
                    expected=norm_exp_stderr[:200],
                    actual=norm_act_stderr[:200],
                    details=diff_text[:1000] if diff_text else "Textual mismatch in stderr",
                    severity="warning",
                )
            )

        # Calculate score (100% minus penalties)
        score = 100.0
        if trace.exit_code != act_exit_code:
            score -= 40.0
        if norm_exp_stdout != norm_act_stdout:
            stdout_sim = compute_similarity_ratio(norm_exp_stdout, norm_act_stdout)
            score -= (1.0 - stdout_sim) * 50.0
        if self.strict_stderr and norm_exp_stderr != norm_act_stderr:
            stderr_sim = compute_similarity_ratio(norm_exp_stderr, norm_act_stderr)
            score -= (1.0 - stderr_sim) * 10.0

        score = max(0.0, min(100.0, score))
        passed = (len(differences) == 0) if self.strict_exit_code else (score >= 95.0)

        return VerificationResult(
            trace_id=trace.id,
            command=full_cmd,
            passed=passed,
            score=score,
            differences=differences,
            duration_ms=duration_ms,
            candidate_stdout=act_stdout,
            candidate_stderr=act_stderr,
            candidate_exit_code=act_exit_code,
        )

    def verify_suite(
        self,
        traces: List[TraceRecord],
        candidate_cmd: List[str],
    ) -> SuiteSummary:
        """Run all traces against candidate implementation and aggregate results."""
        results: List[VerificationResult] = []
        passed_count = 0

        for trace in traces:
            res = self.verify_single(trace, candidate_cmd)
            results.append(res)
            if res.passed:
                passed_count += 1

        total = len(traces)
        failed_count = total - passed_count
        avg_score = (sum(r.score for r in results) / total) if total > 0 else 100.0

        return SuiteSummary(
            total_traces=total,
            passed_traces=passed_count,
            failed_traces=failed_count,
            parity_score=avg_score,
            results=results,
        )


def run_live_differential(
    baseline_cmd: List[str],
    candidate_cmd: List[str],
    stdin: str = "",
    normalizer: Optional[OutputNormalizer] = None,
    timeout: float = 30.0,
) -> Tuple[bool, VerificationResult]:
    """Execute both baseline and candidate side-by-side and compare outputs immediately."""
    from parity_guard.recorder import TraceRecorder

    recorder = TraceRecorder(timeout=timeout)
    golden_trace = recorder.record_execution(
        command=baseline_cmd,
        trace_id="live_differential",
        stdin=stdin,
    )

    verifier = ParityVerifier(normalizer=normalizer, timeout=timeout)
    res = verifier.verify_single(golden_trace, candidate_cmd)
    return res.passed, res
