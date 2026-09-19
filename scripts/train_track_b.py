"""Train, select, evaluate, and persist the R6 Track B model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.artifacts.track_b import write_track_b_artifacts
from src.training.track_b import finalize_track_b, prepare_track_b_run, select_track_b_candidate


def _experiment_id(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", value):
        raise argparse.ArgumentTypeError("experiment ID must be lowercase and path-safe")
    return value


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--experiment-id", type=_experiment_id, default="r6-track-b-v1")
    command.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "artifacts" / "models" / "track_b",
    )
    command.add_argument(
        "--r5-artifact-root",
        type=Path,
        default=ROOT / "artifacts" / "models" / "track_a" / "r5a-track-a-baseline-v1",
    )
    return command


def main() -> int:
    args = parser().parse_args()
    prepared = prepare_track_b_run()
    selection = select_track_b_candidate(prepared)
    result = finalize_track_b(
        selection,
        prepared,
        experiment_id=args.experiment_id,
        r5_artifact_root=args.r5_artifact_root,
    )
    bundle = write_track_b_artifacts(selection, result, prepared, args.output_root)
    print(json.dumps({"bundle": str(bundle), "result": result.to_dict()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
