import numpy as np
import pandas as pd
import pytest

from fraudgraph.models.threshold_tuning import (
    calculate_metrics_at_threshold,
    evaluate_thresholds,
    generate_thresholds,
    select_best_threshold,
)


def test_generate_thresholds_returns_expected_values() -> None:
    thresholds = generate_thresholds(
        threshold_min=0.1,
        threshold_max=0.5,
        threshold_step=0.2,
    )

    assert thresholds == [0.1, 0.3, 0.5]


def test_generate_thresholds_rejects_invalid_range() -> None:
    with pytest.raises(ValueError, match="threshold_min must be smaller"):
        generate_thresholds(
            threshold_min=0.8,
            threshold_max=0.2,
            threshold_step=0.1,
        )


def test_calculate_metrics_at_threshold_returns_expected_metrics() -> None:
    y_true = pd.Series([0, 1, 0, 1])
    y_scores = np.array([0.1, 0.9, 0.2, 0.8])

    metrics = calculate_metrics_at_threshold(
        y_true=y_true,
        y_scores=y_scores,
        threshold=0.5,
    )

    assert metrics["accuracy"] == pytest.approx(1.0)
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(1.0)
    assert metrics["f1"] == pytest.approx(1.0)
    assert metrics["true_positive"] == 2
    assert metrics["true_negative"] == 2
    assert metrics["false_positive"] == 0
    assert metrics["false_negative"] == 0


def test_evaluate_thresholds_returns_one_row_per_threshold() -> None:
    y_true = pd.Series([0, 1, 0, 1])
    y_scores = np.array([0.1, 0.9, 0.2, 0.8])

    thresholds = [0.3, 0.5, 0.7]

    result = evaluate_thresholds(
        y_true=y_true,
        y_scores=y_scores,
        thresholds=thresholds,
    )

    assert len(result) == 3
    assert list(result["threshold"]) == thresholds


def test_select_best_threshold_uses_metric_and_minimum_recall() -> None:
    threshold_results = pd.DataFrame(
        {
            "threshold": [0.2, 0.5, 0.8],
            "precision": [0.30, 0.70, 1.00],
            "recall": [1.00, 0.80, 0.30],
            "f1": [0.46, 0.75, 0.46],
        }
    )

    best = select_best_threshold(
        threshold_results=threshold_results,
        optimization_metric="f1",
        minimum_recall=0.75,
    )

    assert best["threshold"] == pytest.approx(0.5)
    assert best["f1"] == pytest.approx(0.75)


def test_select_best_threshold_raises_when_no_threshold_meets_recall() -> None:
    threshold_results = pd.DataFrame(
        {
            "threshold": [0.2, 0.5, 0.8],
            "precision": [0.30, 0.70, 1.00],
            "recall": [0.60, 0.50, 0.30],
            "f1": [0.40, 0.58, 0.46],
        }
    )

    with pytest.raises(ValueError, match="No threshold satisfies"):
        select_best_threshold(
            threshold_results=threshold_results,
            optimization_metric="f1",
            minimum_recall=0.90,
        )