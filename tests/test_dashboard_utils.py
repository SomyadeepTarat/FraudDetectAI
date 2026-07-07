import pandas as pd
import pytest

from app.dashboard_utils import (
    extract_comparison_table,
    extract_model_metric_table,
    filter_transactions,
    format_number,
    format_percentage,
    get_available_columns,
    summarize_scored_transactions,
)


def test_format_percentage_formats_decimal() -> None:
    assert format_percentage(0.1234) == "12.34%"


def test_format_percentage_handles_none() -> None:
    assert format_percentage(None) == "N/A"


def test_format_number_formats_integer() -> None:
    assert format_number(1234567) == "1,234,567"


def test_format_number_formats_float() -> None:
    assert format_number(1234.5678, decimals=2) == "1,234.57"


def test_extract_model_metric_table_returns_expected_rows() -> None:
    report = {
        "models": {
            "xgboost": {
                "accuracy": 0.99,
                "precision": 0.80,
                "recall": 0.70,
                "f1": 0.75,
                "roc_auc": 0.98,
                "average_precision": 0.85,
            }
        }
    }

    table = extract_model_metric_table(report)

    assert len(table) == 1
    assert table.iloc[0]["model"] == "xgboost"
    assert table.iloc[0]["average_precision"] == pytest.approx(0.85)


def test_extract_comparison_table_returns_expected_rows() -> None:
    report = {
        "model_comparisons": {
            "xgboost": {
                "average_precision": {
                    "baseline": 0.70,
                    "graph_enhanced": 0.85,
                    "absolute_delta": 0.15,
                    "relative_delta_percent": 21.43,
                }
            }
        }
    }

    table = extract_comparison_table(report)

    assert len(table) == 1
    assert table.iloc[0]["model"] == "xgboost"
    assert table.iloc[0]["metric"] == "average_precision"
    assert table.iloc[0]["absolute_delta"] == pytest.approx(0.15)


def test_get_available_columns_returns_only_existing_columns() -> None:
    dataframe = pd.DataFrame(
        {
            "a": [1],
            "b": [2],
        }
    )

    result = get_available_columns(
        dataframe=dataframe,
        preferred_columns=["a", "c", "b"],
    )

    assert result == ["a", "b"]


def test_filter_transactions_filters_by_risk_band_and_probability() -> None:
    dataframe = pd.DataFrame(
        {
            "fraud_probability": [0.95, 0.70, 0.40, 0.10],
            "predicted_fraud": [1, 1, 0, 0],
            "risk_band": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        }
    )

    filtered = filter_transactions(
        dataframe=dataframe,
        risk_bands=["CRITICAL", "HIGH"],
        predicted_fraud_only=True,
        min_probability=0.60,
        max_rows=10,
    )

    assert len(filtered) == 2
    assert list(filtered["risk_band"]) == ["CRITICAL", "HIGH"]


def test_filter_transactions_rejects_invalid_probability() -> None:
    dataframe = pd.DataFrame(
        {
            "fraud_probability": [0.95],
            "predicted_fraud": [1],
            "risk_band": ["CRITICAL"],
        }
    )

    with pytest.raises(ValueError, match="min_probability must be between"):
        filter_transactions(
            dataframe=dataframe,
            min_probability=1.5,
        )


def test_summarize_scored_transactions_returns_expected_summary() -> None:
    dataframe = pd.DataFrame(
        {
            "fraud_probability": [0.95, 0.70, 0.40, 0.10],
            "predicted_fraud": [1, 1, 0, 0],
            "risk_band": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        }
    )

    summary = summarize_scored_transactions(dataframe)

    assert summary["num_transactions"] == 4
    assert summary["num_predicted_fraud"] == 2
    assert summary["average_fraud_probability"] == pytest.approx(0.5375)
    assert summary["max_fraud_probability"] == pytest.approx(0.95)
    assert summary["risk_band_counts"] == {
        "CRITICAL": 1,
        "HIGH": 1,
        "MEDIUM": 1,
        "LOW": 1,
    }