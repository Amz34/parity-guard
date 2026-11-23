"""Diff and normalization engine for parity-guard."""

from __future__ import annotations

import difflib
import json
import re
from typing import Any, List, Optional, Tuple

from parity_guard.models import ParityDifference

# Regex patterns for common non-deterministic runtime tokens
UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
ISO_TIMESTAMP_PATTERN = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)
HEX_HASH_PATTERN = re.compile(r"\b[0-9a-fA-F]{32,64}\b")
TEMP_PATH_PATTERN = re.compile(r"(?:/tmp|/var/tmp|[A-Za-z]:\\(?:Users\\)?[^\\]+\\AppData\\Local\\Temp)/[^\s,;'\"]+")


class OutputNormalizer:
    """Masks volatile runtime tokens (timestamps, UUIDs, temp paths) to ensure stable diffs."""

    def __init__(
        self,
        mask_uuids: bool = True,
        mask_timestamps: bool = True,
        mask_hashes: bool = False,
        mask_temp_paths: bool = True,
        custom_patterns: Optional[List[Tuple[re.Pattern, str]]] = None,
    ):
        self.mask_uuids = mask_uuids
        self.mask_timestamps = mask_timestamps
        self.mask_hashes = mask_hashes
        self.mask_temp_paths = mask_temp_paths
        self.custom_patterns = custom_patterns or []

    def normalize(self, text: str) -> str:
        """Apply configured normalization filters to text."""
        if not text:
            return ""

        result = text
        if self.mask_uuids:
            result = UUID_PATTERN.sub("[UUID_MASKED]", result)
        if self.mask_timestamps:
            result = ISO_TIMESTAMP_PATTERN.sub("[TIMESTAMP_MASKED]", result)
        if self.mask_temp_paths:
            result = TEMP_PATH_PATTERN.sub("[TMPDIR]/masked_path", result)
        if self.mask_hashes:
            result = HEX_HASH_PATTERN.sub("[HASH_MASKED]", result)

        for pat, repl in self.custom_patterns:
            result = pat.sub(repl, result)

        return result


def compare_json_objects(
    expected: Any,
    actual: Any,
    path: str = "$",
    float_tolerance: float = 1e-6,
) -> List[ParityDifference]:
    """Recursively compare structured JSON objects with tolerance for floats and key order."""
    diffs: List[ParityDifference] = []

    if type(expected) != type(actual):
        diffs.append(
            ParityDifference(
                field=f"json:{path}",
                expected=f"{type(expected).__name__}",
                actual=f"{type(actual).__name__}",
                details=f"Type mismatch at {path}: expected {type(expected).__name__}, got {type(actual).__name__}",
            )
        )
        return diffs

    if isinstance(expected, dict):
        exp_keys = set(expected.keys())
        act_keys = set(actual.keys())

        for missing in sorted(exp_keys - act_keys):
            diffs.append(
                ParityDifference(
                    field=f"json:{path}.{missing}",
                    expected=expected[missing],
                    actual=None,
                    details=f"Missing key in candidate output: {path}.{missing}",
                )
            )

        for unexpected in sorted(act_keys - exp_keys):
            diffs.append(
                ParityDifference(
                    field=f"json:{path}.{unexpected}",
                    expected=None,
                    actual=actual[unexpected],
                    details=f"Unexpected key in candidate output: {path}.{unexpected}",
                )
            )

        for common in sorted(exp_keys & act_keys):
            diffs.extend(
                compare_json_objects(
                    expected[common],
                    actual[common],
                    path=f"{path}.{common}",
                    float_tolerance=float_tolerance,
                )
            )

    elif isinstance(expected, list):
        if len(expected) != len(actual):
            diffs.append(
                ParityDifference(
                    field=f"json:{path}",
                    expected=f"length={len(expected)}",
                    actual=f"length={len(actual)}",
                    details=f"Array length mismatch at {path}: expected {len(expected)}, got {len(actual)}",
                )
            )
        min_len = min(len(expected), len(actual))
        for i in range(min_len):
            diffs.extend(
                compare_json_objects(
                    expected[i],
                    actual[i],
                    path=f"{path}[{i}]",
                    float_tolerance=float_tolerance,
                )
            )

    elif isinstance(expected, float) and isinstance(actual, float):
        if abs(expected - actual) > float_tolerance:
            diffs.append(
                ParityDifference(
                    field=f"json:{path}",
                    expected=expected,
                    actual=actual,
                    details=f"Float value outside tolerance at {path}: {expected} vs {actual}",
                )
            )

    else:
        if expected != actual:
            diffs.append(
                ParityDifference(
                    field=f"json:{path}",
                    expected=expected,
                    actual=actual,
                    details=f"Value mismatch at {path}: {expected!r} != {actual!r}",
                )
            )

    return diffs


def compute_string_diff(expected: str, actual: str, label_exp: str = "golden", label_act: str = "candidate") -> str:
    """Generate a unified line diff between two strings."""
    exp_lines = expected.splitlines(keepends=True)
    act_lines = actual.splitlines(keepends=True)
    diff = list(difflib.unified_diff(exp_lines, act_lines, fromfile=label_exp, tofile=label_act))
    return "".join(diff)


def compute_similarity_ratio(expected: str, actual: str) -> float:
    """Calculate character-level similarity ratio between 0.0 and 1.0."""
    if expected == actual:
        return 1.0
    if not expected and not actual:
        return 1.0
    matcher = difflib.SequenceMatcher(None, expected, actual)
    return matcher.ratio()
