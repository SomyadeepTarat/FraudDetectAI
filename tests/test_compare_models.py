import pytest

from fraudgraph.models.compare_models import (
    calculate_metric_delta,
    compare_model_reports,
    compare_single_model_metrics,
    find_best_model_by_metric,
)


def create_baseline_report() -> dict:
    return {
        "models": {
            "logistic_regression": {
                "precision": 0.20,
                "recall": 0.70,
                "f1": 0.31,
                "roc_auc": 0.90,
                "average_precision": 0.40,
            },
            "xgboost": {
                "precision": 0.50,
                "recall": 0.80,
                "f1": 0.62,
                "roc_auc": 0.95,
                "average_precision": 0.70,
            },
        }
    }


def create_graph_report() -> dict:
    return {
        "models": {
            "logistic_regression": {
                "precision": 0.30,
                "recall": 0.75,
                "f1": 0.43,
                "roc_auc": 0.92,
                "average_precision": 0.50,
            },
            "xgboost": {
                "precision": 0.60,
                "recall": 0.85,
                "f1": 0.70,
                "roc_auc": 0.97,
                "average_precision": 0.82,
            },
        }
    }


def test_calculate_metric_delta_returns_absolute_and_relative_delta() -> None:
    result = calculate_metric_delta(
        baseline_value=0.50,
        graph_value=0.75,
    )

    assert result["baseline"] == pytest.approx(0.50)
    assert result["graph_enhanced"] == pytest.approx(0.75)
    assert result["absolute_delta"] == pytest.approx(0.25)
    assert result["relative_delta_percent"] == pytest.approx(50.0)


def test_calculate_metric_delta_handles_zero_baseline() -> None:
    result = calculate_metric_delta(
        baseline_value=0.0,
        graph_value=0.25,
    )

    assert result["baseline"] == pytest.approx(0.0)
    assert result["graph_enhanced"] == pytest.approx(0.25)
    assert result["absolute_delta"] == pytest.approx(0.25)
    assert result["relative_delta_percent"] == pytest.approx(100.0)


def test_compare_single_model_metrics_compares_selected_metrics() -> None:
    baseline_metrics = create_baseline_report()["models"]["xgboost"]
    graph_metrics = create_graph_report()["models"]["xgboost"]

    result = compare_single_model_metrics(
        baseline_metrics=baseline_metrics,
        graph_metrics=graph_metrics,
        metric_names=["precision", "recall"],
    )

    assert result["precision"]["absolute_delta"] == pytest.approx(0.10)
    assert result["recall"]["absolute_delta"] == pytest.approx(0.05)


def test_find_best_model_by_metric_returns_highest_scoring_model() -> None:
    report = create_baseline_report()

    result = find_best_model_by_metric(
        metrics_report=report,
        metric_name="average_precision",
    )

    assert result["model_name"] == "xgboost"
    assert result["score"] == pytest.approx(0.70)


def test_compare_model_reports_returns_expected_structure() -> None:
    baseline_report = create_baseline_report()
    graph_report = create_graph_report()

    result = compare_model_reports(
        baseline_report=baseline_report,
        graph_report=graph_report,
        metric_names=["precision", "recall", "average_precision"],
    )

    assert result["common_models"] == ["logistic_regression", "xgboost"]
    assert result["best_baseline_model_by_average_precision"]["model_name"] == "xgboost"
    assert result["best_graph_model_by_average_precision"]["model_name"] == "xgboost"
    assert "xgboost" in result["model_comparisons"]
    assert result["model_comparisons"]["xgboost"]["average_precision"][
        "absolute_delta"
    ] == pytest.approx(0.12)


def test_compare_model_reports_raises_when_no_common_models() -> None:
    baseline_report = {"models": {"model_a": {"average_precision": 0.5}}}
    graph_report = {"models": {"model_b": {"average_precision": 0.6}}}

    with pytest.raises(ValueError, match="No common model names"):
        compare_model_reports(
            baseline_report=baseline_report,
            graph_report=graph_report,
        )