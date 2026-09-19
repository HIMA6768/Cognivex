"""Train, select, evaluate, and persist the R7 Track C classifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.artifacts.track_c import write_track_c_artifacts
from src.training.track_c import finalize_track_c, prepare_track_c_run, select_track_c_candidate


def _experiment_id(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", value):
        raise argparse.ArgumentTypeError("experiment ID must be lowercase and path-safe")
    return value


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--experiment-id", type=_experiment_id, default="r7-track-c-v1")
    command.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "artifacts" / "models" / "track_c",
    )
    return command


def main() -> int:
    args = parser().parse_args()
    prepared = prepare_track_c_run()
    selection = select_track_c_candidate(prepared.selection)
    result = finalize_track_c(selection, prepared.test, experiment_id=args.experiment_id)
    bundle = write_track_c_artifacts(selection, result, prepared, args.output_root)
    print(json.dumps({"bundle": str(bundle), "result": result.to_dict()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
