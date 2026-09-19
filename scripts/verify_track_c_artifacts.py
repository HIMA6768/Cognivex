"""Read-only verification for a canonical R7 Track C artifact bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.artifacts.track_c import verify_track_c_bundle
from src.training.track_c import prepare_track_c_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True, help="Existing trusted local Track C bundle")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prepared = prepare_track_c_run()
    verification = verify_track_c_bundle(args.bundle, prepared.test)
    print("PASS" if verification.passed else "FAIL")
    print(json.dumps(verification.checks, indent=2, sort_keys=True))
    return 0 if verification.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
