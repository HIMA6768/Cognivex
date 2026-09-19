from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil

from src.artifacts.survival import load_trusted_pickle


R6_RELATIVE = Path("artifacts/models/track_b/r6-track-b-v1")


@dataclass(frozen=True)
class R8SourceFixture:
    repository_root: Path
    bundle: Path
    preprocessor: object
    model: object


def refresh_fixture_checksums(bundle: Path) -> None:
    names = sorted(path.name for path in bundle.iterdir() if path.name != "checksums.sha256")
    (bundle / "checksums.sha256").write_text(
        "".join(
            f"{hashlib.sha256((bundle / name).read_bytes()).hexdigest()}  {name}\n"
            for name in names
        ),
        encoding="utf-8",
    )


def make_r8_source_fixture(tmp_path: Path) -> R8SourceFixture:
    project_root = Path(__file__).resolve().parents[1]
    source = project_root / R6_RELATIVE
    repository_root = tmp_path / "repository"
    bundle = repository_root / R6_RELATIVE
    bundle.mkdir(parents=True)
    for name in (
        "audit.json",
        "feature_contract.json",
        "metadata.json",
        "metrics.json",
        "report.md",
        "validation_leaderboard.csv",
    ):
        shutil.copyfile(source / name, bundle / name)
    (bundle / "preprocessor.pkl").write_bytes(b"verified-test-preprocessor")
    (bundle / "cox_model.pkl").write_bytes(b"verified-test-model")
    refresh_fixture_checksums(bundle)
    return R8SourceFixture(
        repository_root=repository_root,
        bundle=bundle,
        preprocessor=load_trusted_pickle(source / "preprocessor.pkl", trusted=True),
        model=load_trusted_pickle(source / "cox_model.pkl", trusted=True),
    )


def replace_json(bundle: Path, name: str, mutate) -> None:
    path = bundle / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    refresh_fixture_checksums(bundle)
