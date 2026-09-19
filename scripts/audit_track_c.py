"""Run and persist the independent 28-check R7 Track C audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit.track_c import audit_persisted_track_c, read_pytest_summary, write_track_c_audit


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument(
        "--bundle",
        type=Path,
        default=ROOT / "artifacts/models/track_c/r7-track-c-v1",
    )
    command.add_argument("--full-test-suite-summary-file", type=Path, required=True)
    return command


def main() -> int:
    args = parser().parse_args()
    passed, summary = read_pytest_summary(args.full_test_suite_summary_file)
    audit = audit_persisted_track_c(
        args.bundle,
        repository_root=ROOT,
        full_test_suite_passed=passed,
        full_test_suite_summary=summary,
    )
    write_track_c_audit(args.bundle, audit)
    print(json.dumps(audit.to_dict(), indent=2))
    return 0 if audit.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
