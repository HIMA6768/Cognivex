"""R4D mutation representation, selector, and burden transformer tests."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone

from src.preprocessing.mutations import (
    MutationAnnotationKind,
    MutationBurdenTransformer,
    MutationFrequencySelector,
    classify_mutation_annotation,
)


@pytest.mark.parametrize("value", ["0", " 0 ", 0, 0.0, -0.0])
def test_zero_mutation_representations_are_absent(value: object) -> None:
    """Treating numeric-looking zero as annotation magnitude would create false mutations."""
    kind, annotation = classify_mutation_annotation(value)

    assert kind is MutationAnnotationKind.ABSENT
    assert annotation is None


@pytest.mark.parametrize("value", ["H1047R", " frameshift ", 1, -2.5])
def test_nonzero_annotations_are_binary_presence_not_magnitude(value: object) -> None:
    """The raw annotation identity or numeric value must never become predictor magnitude."""
    kind, annotation = classify_mutation_annotation(value)

    assert kind is MutationAnnotationKind.PRESENT
    assert annotation is not None


@pytest.mark.parametrize("value", [None, np.nan, "", "   "])
def test_blank_mutation_representations_are_missing(value: object) -> None:
    """Silently treating missing mutation annotations as absence would change burden and prevalence."""
    kind, annotation = classify_mutation_annotation(value)

    assert kind is MutationAnnotationKind.MISSING
    assert annotation is None


@pytest.mark.parametrize("value", [True, False, float("inf"), float("-inf"), "NaN"])
def test_malformed_mutation_representations_fail_clearly(value: object) -> None:
    """Boolean or non-finite mutation values have no approved canonical interpretation."""
    with pytest.raises(ValueError, match="mutation annotation"):
        classify_mutation_annotation(value)


def _selector_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "above_mut": ["A", "B", *("0" for _ in range(18))],
            "boundary_mut": ["A", *("0" for _ in range(19))],
            "below_mut": ["0"] * 20,
        }
    )


def test_selector_uses_inclusive_fit_only_prevalence_and_stable_source_order() -> None:
    """Using holdout frequency or a strict greater-than boundary would leak or drop a 5% gene."""
    train = _selector_frame()
    selector = MutationFrequencySelector(tuple(train.columns), min_prevalence=0.05)
    selector.fit(train)

    assert selector.fit_row_count_ == 20
    assert selector.prevalence_by_column_ == (
        ("above_mut", 0.10),
        ("boundary_mut", 0.05),
        ("below_mut", 0.0),
    )
    assert selector.retained_columns_ == ("above_mut", "boundary_mut")
    assert selector.excluded_columns_ == ("below_mut",)
    assert selector.get_feature_names_out().tolist() == [
        "above_mut_present",
        "boundary_mut_present",
    ]

    validation = pd.DataFrame(
        {
            "above_mut": ["0", "0"],
            "boundary_mut": ["0", "0"],
            "below_mut": ["X", "Y"],
        }
    )
    transformed = selector.transform(validation)

    np.testing.assert_array_equal(transformed, [[0.0, 0.0], [0.0, 0.0]])
    assert selector.retained_columns_ == ("above_mut", "boundary_mut")


def test_separately_fitted_folds_may_retain_different_boundary_genes() -> None:
    """Freezing the full-training gene set would prevent correct fold-local selection."""
    first_fold = pd.DataFrame({"gene_mut": ["M", *("0" for _ in range(19))]})
    second_fold = pd.DataFrame({"gene_mut": ["0"] * 20})

    first = MutationFrequencySelector(("gene_mut",), min_prevalence=0.05).fit(first_fold)
    second = MutationFrequencySelector(("gene_mut",), min_prevalence=0.05).fit(second_fold)

    assert first.retained_columns_ == ("gene_mut",)
    assert second.retained_columns_ == ()


def test_selector_is_cloneable_and_rejects_missing_or_invalid_annotations() -> None:
    """A non-cloneable selector or silent mutation imputation would be unsafe inside future CV."""
    selector = MutationFrequencySelector(("gene_mut",), min_prevalence=0.05)
    cloned = clone(selector)

    assert cloned is not selector
    assert cloned.mutation_columns == ("gene_mut",)
    with pytest.raises(ValueError, match="missing mutation annotation"):
        selector.fit(pd.DataFrame({"gene_mut": ["0", None]}))
    with pytest.raises(ValueError, match="invalid mutation annotation"):
        selector.fit(pd.DataFrame({"gene_mut": ["0", True]}))


def test_burden_counts_all_declared_genes_and_emits_only_log1p() -> None:
    """Restricting burden to frequency-selected genes would make its meaning fold-dependent."""
    frame = pd.DataFrame(
        {
            "common_mut": ["0", "A", "A"],
            "rare_mut": ["0", "B", "B"],
            "other_mut": ["0", "0", "C"],
        }
    )
    transformer = MutationBurdenTransformer(tuple(frame.columns))
    transformed = transformer.fit_transform(frame)

    assert transformer.get_feature_names_out().tolist() == ["mutation_burden_log1p"]
    np.testing.assert_allclose(
        transformed[:, 0],
        [0.0, math.log1p(2), math.log1p(3)],
    )


def test_burden_transformer_is_cloneable_and_fails_on_missing_values() -> None:
    """A missing source gene cannot silently reduce a patient's mutation burden."""
    transformer = MutationBurdenTransformer(("gene_a_mut", "gene_b_mut"))

    assert clone(transformer) is not transformer
    with pytest.raises(ValueError, match="missing mutation annotation"):
        transformer.fit_transform(
            pd.DataFrame({"gene_a_mut": ["A"], "gene_b_mut": [np.nan]})
        )
