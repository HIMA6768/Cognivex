"""Run and persist the independent 30-check R8 prognostic feature audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit.prognostic_features import write_prognostic_feature_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument(
        "--source-bundle",
        type=Path,
        default=ROOT / "artifacts/models/track_b/r6-track-b-v1",
    )
    parser.add_argument("--full-test-suite-summary-file", type=Path, required=True)
    parser.add_argument("--full-test-suite-passed", action="store_true")
    return parser.parse_args()


def _summary(path: Path) -> str:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    matches = [line for line in lines if re.search(r"\b\d+ passed\b", line)]
    if not matches:
        return "FAILED: full-suite evidence contains no passed-summary line"
    return matches[-1]


def main() -> int:
    args = parse_args()
    summary = _summary(args.full_test_suite_summary_file)
    if not args.full_test_suite_passed:
        summary = f"FAILED: {summary}"
    try:
        report = write_prognostic_feature_audit(
            args.bundle,
            args.source_bundle,
            ROOT,
            summary,
        )
    except Exception as error:
        print(f"BLOCKED: {error}")
        return 1
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
