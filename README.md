# parity-guard

[![CI](https://github.com/Amz34/parity-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/Amz34/parity-guard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> Behavioral parity verification and differential testing engine for code rewrites, language ports, and runtime migrations.

![Parity Guard Architecture](assets/parity-guard-overview.jpg)

## Why Parity Guard?

Rewriting legacy systems into modern languages (such as porting Python or Node.js services to Rust or Go) carries significant behavioral regression risk. Edge cases, subtle exit-code differences, dynamic timestamp formatting, and modified error messages frequently escape conventional test suites.

`parity-guard` solves this by recording deterministic golden behavioral traces from the baseline implementation and executing candidate binaries against those traces under identical execution environments. It features automated normalization for volatile tokens (UUIDs, timestamps, temp paths), structured JSON diffing with floating-point tolerance, and automated parity scoring for CI/CD gates.

## Key Features

- **Zero External Dependencies:** Built entirely on the Python standard library; runs immediately in any standard container or CI runner.
- **Golden Trace Recording:** Captures command-line arguments, environment variables, standard input, standard output, standard error, exit codes, and duration in portable JSON suites.
- **Live Differential Execution:** Runs baseline and candidate binaries concurrently with identical inputs and outputs immediate line-by-line unified diffs.
- **Smart Normalization:** Automatically masks volatile runtime tokens including RFC-3339 timestamps, UUID v4 strings, and dynamic temp directory paths without breaking structured assertions.
- **Semantic JSON Diffing:** Recursively evaluates JSON outputs, handling unordered object keys and configurable floating-point tolerances.
- **CI/CD Quality Gate:** Computes precise parity scores (from 0 to 100) and emits exit codes compatible with automated merge requirements.
- **Audit Reporting:** Generates GitHub-flavored Markdown reports documenting every passed, warned, and failed behavioral test case.

![Continuous Verification Pipeline](assets/github-benefits-cicd.jpg)

## Quickstart

### Installation

Clone the repository and install locally:

```bash
git clone https://github.com/Amz34/parity-guard.git
cd parity-guard
python3 -m pip install -e .
```

Alternatively, invoke directly via module syntax without installation:

```bash
python3 -m parity_guard --help
```

### 1. Record Golden Traces from Baseline

Capture execution traces from your legacy script or CLI application:

```bash
parity-guard record \
  --cmd "python3 legacy_tool.py --format json --input sample.csv" \
  --trace-id "csv_export_json" \
  --suite "tests/fixtures/parity_suite.json" \
  --tag "data-pipeline"
```

### 2. Verify Candidate Implementation

Run your rewritten implementation (e.g., compiled binary or new service) against the golden suite:

```bash
parity-guard verify \
  --suite "tests/fixtures/parity_suite.json" \
  --cmd "./bin/candidate-tool" \
  --threshold 100 \
  --report "audit_report.md"
```

If the candidate produces matching exit codes, stdout, and normalized JSON structures, `parity-guard` outputs:

```text
--- Parity Verification Summary ---
Traces Tested: 1
Passed:        1
Failed:        0
Parity Score:  100.0%
Threshold:     100.0%
```

### 3. Live Differential Execution

Compare baseline and candidate behaviors side-by-side on any command:

```bash
parity-guard diff \
  --baseline "python3 legacy_tool.py calculate --val 10" \
  --candidate "./bin/candidate-tool calculate --val 10"
```

## How It Works

```text
+-----------------------+              +-----------------------+
|  Baseline Executable  |              | Candidate Executable  |
+-----------+-----------+              +-----------+-----------+
            |                                      |
            v                                      v
   [ Execution Trace ]                    [ Candidate Execution ]
    - stdin / stdout                       - stdin / stdout
    - exit code / stderr                   - exit code / stderr
    - execution latency                    - execution latency
            |                                      |
            +------------------+-------------------+
                               |
                               v
                     +-------------------+
                     | Output Normalizer |
                     | (Mask Volatiles)  |
                     +---------+---------+
                               |
                               v
                     +-------------------+
                     |  Parity Oracle    |
                     | - Semantic JSON   |
                     | - Unified Diff    |
                     | - Score Engine    |
                     +---------+---------+
                               |
                               v
                     +-------------------+
                     | CI Gate & Report  |
                     | (Confidence Score)|
                     +-------------------+
```

1. **Trace Capture (`TraceRecorder`):** Executes the baseline process via subprocess isolation, capturing raw streams and timing data.
2. **Token Normalization (`OutputNormalizer`):** Replaces non-deterministic strings (timestamps, UUIDs, temporary paths) with deterministic placeholders before semantic evaluation.
3. **Structured Comparison (`compare_json_objects`):** If outputs parse as JSON, validates structural keys and values independently of key ordering.
4. **Scoring & Assertions (`ParityVerifier`):** Weights exit-code mismatches, stdout discrepancies, and stderr warnings to calculate a parity confidence score.

## Command Reference

| Command | Key Arguments | Purpose |
|---|---|---|
| `record` | `--cmd`, `--suite`, `--trace-id`, `--stdin`, `--tag` | Capture baseline execution trace into a suite JSON file |
| `verify` | `--suite`, `--cmd`, `--threshold`, `--report`, `--strict-stderr` | Replay candidate against suite and verify behavioral parity |
| `diff` | `--baseline`, `--candidate`, `--stdin`, `--json` | Compare baseline and candidate outputs side-by-side |
| `audit` | `--suite` | Inspect trace count, metadata, and tags in a suite file |

## Verification & Testing

Run unit tests and lint checks:

```bash
make test
make lint
```

## Limitations

- **Interactive TTY Programs:** Terminal control escape sequences (ncurses, interactive password prompts) require automated test wrappers or non-interactive flags.
- **Long-Running Daemons:** Designed for CLI tools, batch processes, and request-response commands rather than continuous background services.

## Related Infrastructure

- [awesome-agent-infrastructure](https://github.com/Amz34/awesome-agent-infrastructure) — Curated directory of production-grade building blocks for autonomous AI systems.
- [superagent-core](https://github.com/Amz34/superagent-core) — Lightweight, zero-dependency autonomous agent execution engine.
- [diskopt](https://github.com/Amz34/diskopt) — Zero-dependency storage optimization CLI and SRE guardrail engine.
- [cron-stabilizer](https://github.com/Amz34/cron-stabilizer) — Fleet automation stabilizer converting Linux crontabs into hardened systemd timer units.

## License

[MIT](LICENSE) © 2026 Amz34
