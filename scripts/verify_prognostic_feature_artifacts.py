"""Read-only verification for an R8 prognostic feature artifact bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.artifacts.prognostic_features import verify_prognostic_feature_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument(
        "--source-bundle",
        type=Path,
        default=ROOT / "artifacts/models/track_b/r6-track-b-v1",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    verification = verify_prognostic_feature_bundle(args.bundle, args.source_bundle, ROOT)
    print("PASS" if verification.passed else "FAIL")
    print(json.dumps(dict(sorted(verification.checks.items())), indent=2))
    return 0 if verification.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
