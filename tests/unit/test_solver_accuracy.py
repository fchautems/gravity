from __future__ import annotations

import numpy as np
import pytest

from gravity.diagnostics import compare_accelerations


def test_known_relative_errors_produce_expected_report() -> None:
    reference = np.array([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0]], dtype=np.float64)
    approximate = np.array([[1.01, 0.0, 0.0], [0.0, 1.9, 0.0]], dtype=np.float64)
    report = compare_accelerations(reference, approximate)
    assert report.sample_count == report.relative_sample_count == 2
    assert report.near_zero_sample_count == 0
    assert report.median_relative_error == pytest.approx(0.03)
    assert report.percentile_95_relative_error == pytest.approx(0.048)
    assert report.maximum_relative_error == pytest.approx(0.05)
    assert not report.meets_v1_budget()
    assert report.meets_v1_budget(median_limit=0.031)


def test_near_zero_references_are_reported_as_absolute_error_only() -> None:
    reference = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0]], dtype=np.float64)
    approximate = np.array([[0.001, 0.0, 0.0], [2.02, 0.0, 0.0]], dtype=np.float64)
    report = compare_accelerations(reference, approximate, relative_floor=1.0e-6)
    assert report.relative_sample_count == 1
    assert report.near_zero_sample_count == 1
    assert report.median_relative_error == pytest.approx(0.01)
    assert report.maximum_near_zero_absolute_error == pytest.approx(0.001)


def test_all_zero_reference_has_a_finite_empty_relative_report() -> None:
    reference = np.zeros((3, 3), dtype=np.float64)
    approximate = np.full((3, 3), 1.0e-9, dtype=np.float64)
    report = compare_accelerations(reference, approximate)
    assert report.relative_sample_count == 0
    assert report.median_relative_error == 0.0
    assert report.maximum_near_zero_absolute_error == pytest.approx(np.sqrt(3.0) * 1.0e-9)
    assert not report.meets_v1_budget()


@pytest.mark.parametrize(
    ("reference", "approximate", "floor", "error"),
    [
        (np.zeros((0, 3)), np.zeros((0, 3)), None, ValueError),
        (np.zeros((2, 2)), np.zeros((2, 2)), None, ValueError),
        (np.zeros((2, 3), dtype=np.float32), np.zeros((2, 3)), None, TypeError),
        (np.zeros((2, 3)), np.zeros((3, 3)), None, ValueError),
        (np.full((2, 3), np.nan), np.zeros((2, 3)), None, ValueError),
        (np.zeros((2, 3)), np.zeros((2, 3)), -1.0, ValueError),
        (np.zeros((2, 3)), np.zeros((2, 3)), object(), TypeError),
    ],
)
def test_accuracy_report_boundaries_are_validated(
    reference: np.ndarray,
    approximate: np.ndarray,
    floor: object,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        compare_accelerations(reference, approximate, relative_floor=floor)  # type: ignore[arg-type]
