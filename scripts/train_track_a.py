"""Fit and persist the approved R5A clinical-only Cox PH baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.artifacts.survival import write_track_a_artifacts
from src.data.metabric import MetabricPaths
from src.training.track_a import TrackAFitStopped, fit_track_a, prepare_track_a_run


DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "artifacts" / "models" / "track_a"
_SAFE_EXPERIMENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def validate_experiment_id(value: str) -> str:
    """Return a filesystem-safe experiment ID or fail before creating artifacts."""
    if not isinstance(value, str) or not _SAFE_EXPERIMENT_ID.fullmatch(value):
        raise ValueError(
            "experiment ID must be 1-128 characters, begin with an alphanumeric "
            "character, and contain only letters, digits, '.', '_', or '-'"
        )
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fit the approved unpenalized Track A Cox PH baseline."
    )
    parser.add_argument("--experiment-id", required=True, type=validate_experiment_id)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    prepared = prepare_track_a_run(MetabricPaths.from_repository_root(REPOSITORY_ROOT))
    try:
        bundle = fit_track_a(prepared, args.experiment_id)
    except TrackAFitStopped as error:
        print(
            json.dumps(
                {
                    "status": "STOPPED",
                    "message": str(error),
                    "matrix_diagnostic": error.matrix_diagnostic.to_dict(),
                    "convergence_warnings": list(error.convergence_warnings),
                    "fallback_applied": False,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    records = write_track_a_artifacts(
        bundle.preprocessor,
        bundle.model,
        bundle.result,
        args.output_root,
    )
    print(
        json.dumps(
            {
                "status": "COMPLETED",
                "experiment_id": bundle.result.experiment_id,
                "bundle": str((args.output_root / bundle.result.experiment_id).resolve()),
                "validation_c_index": bundle.result.validation_metric.c_index,
                "test_scored": bundle.result.test_scored,
                "artifacts": [record.to_dict() for record in records],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
