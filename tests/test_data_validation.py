import pandas as pd
import pytest

from fraudgraph.data.validate_data import (
    assert_valid_dataset,
    check_binary_target,
    check_numeric_columns,
    check_required_columns,
    create_validation_report,
    summarize_missing_values,
    summarize_target_distribution,
)


def create_sample_valid_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "step": [1, 1, 2],
            "type": ["PAYMENT", "TRANSFER", "CASH_OUT"],
            "amount": [100.0, 250.0, 300.0],
            "nameOrig": ["C1", "C2", "C3"],
            "oldbalanceOrg": [1000.0, 500.0, 300.0],
            "newbalanceOrig": [900.0, 250.0, 0.0],
            "nameDest": ["M1", "C4", "C5"],
            "oldbalanceDest": [0.0, 100.0, 50.0],
            "newbalanceDest": [0.0, 350.0, 350.0],
            "isFraud": [0, 0, 1],
            "isFlaggedFraud": [0, 0, 0],
        }
    )


def test_check_required_columns_returns_empty_list_for_valid_dataframe() -> None:
    dataframe = create_sample_valid_dataframe()
    required_columns = list(dataframe.columns)

    missing_columns = check_required_columns(dataframe, required_columns)

    assert missing_columns == []


def test_check_required_columns_detects_missing_columns() -> None:
    dataframe = create_sample_valid_dataframe().drop(columns=["isFraud"])
    required_columns = [
        "step",
        "type",
        "amount",
        "nameOrig",
        "nameDest",
        "isFraud",
    ]

    missing_columns = check_required_columns(dataframe, required_columns)

    assert missing_columns == ["isFraud"]


def test_check_numeric_columns_detects_invalid_dtype() -> None:
    dataframe = create_sample_valid_dataframe()
    dataframe["amount"] = dataframe["amount"].astype(str)

    invalid_columns = check_numeric_columns(dataframe, ["amount", "step"])

    assert invalid_columns == {"amount": "str"}


def test_check_binary_target_accepts_zero_and_one() -> None:
    dataframe = create_sample_valid_dataframe()

    result = check_binary_target(dataframe, "isFraud", {0, 1})

    assert result["exists"] is True
    assert result["valid"] is True
    assert result["unique_values"] == [0, 1]
    assert result["invalid_values"] == []


def test_check_binary_target_rejects_unexpected_value() -> None:
    dataframe = create_sample_valid_dataframe()
    dataframe.loc[0, "isFraud"] = 2

    result = check_binary_target(dataframe, "isFraud", {0, 1})

    assert result["exists"] is True
    assert result["valid"] is False
    assert result["invalid_values"] == [2]


def test_summarize_missing_values_counts_only_columns_with_missing_values() -> None:
    dataframe = create_sample_valid_dataframe()
    dataframe.loc[1, "amount"] = None
    dataframe.loc[2, "type"] = None

    result = summarize_missing_values(dataframe)

    assert result == {"type": 1, "amount": 1}


def test_summarize_target_distribution_returns_counts_and_positive_rate() -> None:
    dataframe = create_sample_valid_dataframe()

    result = summarize_target_distribution(dataframe, "isFraud")

    assert result["exists"] is True
    assert result["counts"] == {"0": 2, "1": 1}
    assert result["positive_rate"] == pytest.approx(1 / 3)


def test_create_validation_report_marks_valid_dataset_as_valid() -> None:
    dataframe = create_sample_valid_dataframe()

    report = create_validation_report(
        dataframe=dataframe,
        required_columns=list(dataframe.columns),
        numeric_columns=[
            "step",
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest",
            "isFraud",
            "isFlaggedFraud",
        ],
        target_column="isFraud",
    )

    assert report["is_valid"] is True
    assert report["num_rows"] == 3
    assert report["num_columns"] == 11


def test_assert_valid_dataset_raises_error_for_invalid_report() -> None:
    report = {
        "is_valid": False,
        "missing_required_columns": ["isFraud"],
        "invalid_numeric_columns": {},
        "target_check": {"valid": True},
    }

    with pytest.raises(ValueError, match="Dataset validation failed"):
        assert_valid_dataset(report)