"""parity-guard: Differential testing and behavioral parity verification engine."""

__version__ = "1.0.0"

from parity_guard.diff import OutputNormalizer, compare_json_objects, compute_string_diff
from parity_guard.models import ParityDifference, SuiteSummary, TraceRecord, VerificationResult
from parity_guard.recorder import SuiteStorage, TraceRecorder
from parity_guard.verifier import ParityVerifier, run_live_differential

__all__ = [
    "OutputNormalizer",
    "compare_json_objects",
    "compute_string_diff",
    "ParityDifference",
    "SuiteSummary",
    "TraceRecord",
    "VerificationResult",
    "SuiteStorage",
    "TraceRecorder",
    "ParityVerifier",
    "run_live_differential",
]
