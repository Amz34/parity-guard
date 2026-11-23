"""Trace recording engine for parity-guard."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from parity_guard.models import TraceRecord


class TraceRecorder:
    """Executes baseline commands and records reproducible golden traces."""

    def __init__(self, working_dir: Optional[str] = None, timeout: float = 30.0):
        self.working_dir = working_dir or os.getcwd()
        self.timeout = timeout

    def record_execution(
        self,
        command: List[str],
        trace_id: str,
        stdin: str = "",
        env: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceRecord:
        """Run the command and record stdout, stderr, exit code, and duration."""
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                command,
                input=stdin,
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                env=merged_env,
                timeout=self.timeout,
            )
            duration_ms = (time.perf_counter() - start) * 1000.0
            return TraceRecord(
                id=trace_id,
                command=command,
                stdin=stdin,
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                env=env or {},
                tags=tags or [],
                metadata=metadata or {},
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = (time.perf_counter() - start) * 1000.0
            stdout_str = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr_str = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            return TraceRecord(
                id=trace_id,
                command=command,
                stdin=stdin,
                stdout=stdout_str,
                stderr=stderr_str + f"\n[TIMED_OUT after {self.timeout}s]",
                exit_code=-9,
                duration_ms=duration_ms,
                env=env or {},
                tags=tags or [],
                metadata={"error": "timeout", **(metadata or {})},
            )


class SuiteStorage:
    """Persists and retrieves collections of golden trace records."""

    @staticmethod
    def load_suite(path: str) -> List[TraceRecord]:
        """Load a list of trace records from a JSON file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Suite file not found: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "traces" in data:
            records = data["traces"]
        elif isinstance(data, list):
            records = data
        else:
            raise ValueError(f"Invalid suite format in {path}: expected list or dict with 'traces' key")

        return [TraceRecord.from_dict(item) for item in records]

    @staticmethod
    def save_suite(path: str, traces: List[TraceRecord], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save a list of trace records to a JSON file."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": "1.0.0",
            "metadata": metadata or {},
            "total_traces": len(traces),
            "traces": [t.to_dict() for t in traces],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
