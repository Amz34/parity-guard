"""Data models for parity-guard behavioral verification."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TraceRecord:
    """Golden execution trace captured from a baseline implementation."""
    id: str
    command: List[str]
    stdin: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0
    env: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceRecord":
        return cls(
            id=data.get("id", ""),
            command=data.get("command", []),
            stdin=data.get("stdin", ""),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            exit_code=data.get("exit_code", 0),
            duration_ms=data.get("duration_ms", 0.0),
            env=data.get("env", {}),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ParityDifference:
    """Specific behavioral discrepancy between baseline and candidate."""
    field: str
    expected: Any
    actual: Any
    details: str = ""
    severity: str = "error"  # error, warning, info

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    """Result of verifying one candidate execution against a golden trace."""
    trace_id: str
    command: List[str]
    passed: bool
    score: float
    differences: List[ParityDifference] = field(default_factory=list)
    duration_ms: float = 0.0
    candidate_stdout: str = ""
    candidate_stderr: str = ""
    candidate_exit_code: int = 0

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["differences"] = [d.to_dict() for d in self.differences]
        return res


@dataclass
class SuiteSummary:
    """Aggregated results across all traces in a verification suite."""
    total_traces: int
    passed_traces: int
    failed_traces: int
    parity_score: float
    results: List[VerificationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_traces": self.total_traces,
            "passed_traces": self.passed_traces,
            "failed_traces": self.failed_traces,
            "parity_score": round(self.parity_score, 2),
            "results": [r.to_dict() for r in self.results],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Parity Verification Audit Report",
            "",
            f"- **Total Traces:** {self.total_traces}",
            f"- **Passed:** {self.passed_traces}",
            f"- **Failed:** {self.failed_traces}",
            f"- **Parity Score:** {self.parity_score:.1f}%",
            "",
            "| Trace ID | Status | Exit Code (Exp/Act) | Parity Score | Discrepancies |",
            "|---|---|---|---|---|",
        ]
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            diff_count = len(r.differences)
            diff_desc = ", ".join(d.field for d in r.differences) if diff_count else "None"
            exp_ec = r.differences[0].expected if any(d.field == "exit_code" for d in r.differences) else r.candidate_exit_code
            lines.append(
                f"| `{r.trace_id}` | {status} | `{exp_ec}` / `{r.candidate_exit_code}` | {r.score:.1f}% | {diff_desc} |"
            )
        return "\n".join(lines)
