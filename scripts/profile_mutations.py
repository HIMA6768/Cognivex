"""Generate R4D-P0 locked-training mutation evidence artifacts."""

from __future__ import annotations

from pathlib import Path

from src.data.mutation_profile import profile_canonical_mutations, write_mutation_profile_artifacts


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    result = profile_canonical_mutations()
    artifacts = write_mutation_profile_artifacts(result, REPOSITORY_ROOT / "results")
    for path in (
        artifacts.per_gene_csv,
        artifacts.burden_csv,
        artifacts.summary_json,
        artifacts.markdown,
    ):
        print(path.relative_to(REPOSITORY_ROOT))


if __name__ == "__main__":
    main()
