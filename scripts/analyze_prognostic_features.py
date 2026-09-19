"""Generate one aggregate R8 analysis from the frozen canonical R6 Track B model."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analysis.prognostic_features import (
    build_genomic_feature_mapping,
    extract_prognostic_feature_effects,
    validate_genomic_mapping_authorities,
)
from src.artifacts.prognostic_features import (
    verify_and_load_track_b_source,
    write_prognostic_feature_bundle,
)


_ANALYSIS_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")


def _analysis_id(value: str) -> str:
    if not _ANALYSIS_ID.fullmatch(value) or value in {".", ".."}:
        raise argparse.ArgumentTypeError(
            "analysis ID must match [a-z0-9][a-z0-9._-]* and cannot be a parent segment"
        )
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-id",
        type=_analysis_id,
        default="r8-prognostic-features-v1",
    )
    parser.add_argument(
        "--source-bundle",
        type=Path,
        default=ROOT / "artifacts/models/track_b/r6-track-b-v1",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "artifacts/analysis",
    )
    return parser.parse_args()


def run_analysis(*, analysis_id: str, source_bundle: Path, output_root: Path) -> dict[str, object]:
    """Execute verify, map, extract, and persist in the approved no-fit order."""
    _analysis_id(analysis_id)
    source = verify_and_load_track_b_source(source_bundle, ROOT)
    mapping = build_genomic_feature_mapping(source.feature_contract, source.model_feature_names)
    validate_genomic_mapping_authorities(mapping, source)
    result = extract_prognostic_feature_effects(source, mapping)
    if result.analysis_id != analysis_id:
        result = replace(result, analysis_id=analysis_id)
    bundle = write_prognostic_feature_bundle(result, source, output_root)
    active = sum(effect.is_active for effect in result.effects)
    return {
        "bundle": str(bundle),
        "analysis_id": result.analysis_id,
        "total": len(result.effects),
        "active": active,
        "effectively_zero": len(result.effects) - active,
    }


def main() -> int:
    args = parse_args()
    try:
        payload = run_analysis(
            analysis_id=args.analysis_id,
            source_bundle=args.source_bundle,
            output_root=args.output_root,
        )
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
