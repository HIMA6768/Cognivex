"""Run and persist the independent 25-check R6 Track B audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit.track_b import audit_persisted_track_b, write_track_b_audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle",
        type=Path,
        default=ROOT / "artifacts" / "models" / "track_b" / "r6-track-b-v1",
    )
    parser.add_argument("--full-test-suite-passed", action="store_true")
    parser.add_argument("--full-test-suite-summary", default="not supplied")
    args = parser.parse_args()
    audit = audit_persisted_track_b(
        args.bundle,
        repository_root=ROOT,
        full_test_suite_passed=args.full_test_suite_passed,
        full_test_suite_summary=args.full_test_suite_summary,
    )
    write_track_b_audit(args.bundle, audit)
    print(json.dumps(audit.to_dict(), indent=2))
    return 0 if audit.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
