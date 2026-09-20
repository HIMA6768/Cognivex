"""Write or read-only verify R9 inference-service audit evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit.inference_service import verify_inference_service_audit, write_inference_service_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--full-test-suite-summary-file", type=Path)
    parser.add_argument("--full-test-suite-passed", action="store_true")
    args = parser.parse_args()
    root = ROOT
    if args.verify:
        verify_inference_service_audit(root)
        print("PASS: final R9 audit evidence verifies")
        return 0
    if args.full_test_suite_summary_file is None or not args.full_test_suite_passed:
        parser.error("a write requires --full-test-suite-summary-file and --full-test-suite-passed")
    report = write_inference_service_audit(root, args.full_test_suite_summary_file.read_text(encoding="utf-8"), bootstrap=args.bootstrap)
    print(f"{report.status}: mode={report.mode} checks={sum(check.passed for check in report.checks)}/31")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
