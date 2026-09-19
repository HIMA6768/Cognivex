"""Generate the read-only R6-P0 engineer compatibility report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from src.data.engineer_compatibility import audit_repository, write_audit_artifacts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit imported cognivex_ml code against active Cognivex data without training."
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=REPOSITORY_ROOT / "artifacts" / "r6_p0",
    )
    parser.add_argument(
        "--engineer-source-ref",
        default="origin/anay/prediction_pipelines",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = audit_repository(
        REPOSITORY_ROOT,
        engineer_source_ref=args.engineer_source_ref,
    )
    json_path, markdown_path = write_audit_artifacts(report, args.output_directory)
    print(
        json.dumps(
            {
                "status": report["status"],
                "recommendation": report["recommendation"],
                "json_report": str(json_path.resolve()),
                "markdown_report": str(markdown_path.resolve()),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
