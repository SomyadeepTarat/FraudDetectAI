import pandas as pd
import pytest

from fraudgraph.eda.eda_summary import (
    calculate_balance_behavior_summary,
    calculate_class_distribution,
    calculate_numeric_feature_summary,
    calculate_transaction_type_summary,
    create_eda_summary,
)


def create_sample_cleaned_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "step": [1, 1, 2, 2, 3],
            "type": ["PAYMENT", "TRANSFER", "CASH_OUT", "TRANSFER", "CASH_OUT"],
            "amount": [100.0, 1000.0, 500.0, 800.0, 700.0],
            "nameOrig": ["C1", "C2", "C3", "C4", "C5"],
            "oldbalanceOrg": [1000.0, 1000.0, 500.0, 800.0, 700.0],
            "newbalanceOrig": [900.0, 0.0, 0.0, 0.0, 0.0],
            "nameDest": ["M1", "C6", "C7", "C8", "C9"],
            "oldbalanceDest": [0.0, 0.0, 100.0, 10.0, 50.0],
            "newbalanceDest": [0.0, 1000.0, 600.0, 810.0, 750.0],
            "isFraud": [0, 1, 0, 1, 1],
            "isFlaggedFraud": [0, 0, 0, 0, 0],
            "origin_balance_delta": [100.0, 1000.0, 500.0, 800.0, 700.0],
            "destination_balance_delta": [0.0, 1000.0, 500.0, 800.0, 700.0],
            "amount_to_old_origin_balance_ratio": [0.1, 1.0, 1.0, 1.0, 1.0],
            "amount_to_old_destination_balance_ratio": [
                100000000000.0,
                1000000000000.0,
                5.0,
                80.0,
                14.0,
            ],
            "is_origin_balance_emptied": [0, 1, 1, 1, 1],
            "is_destination_balance_unchanged": [1, 0, 0, 0, 0],
            "is_transfer_type": [0, 1, 0, 1, 0],
            "is_cashout_type": [0, 0, 1, 0, 1],
        }
    )


def test_calculate_class_distribution_returns_counts_and_percentages() -> None:
    dataframe = create_sample_cleaned_dataframe()

    result = calculate_class_distribution(dataframe, "isFraud")

    assert result["total_rows"] == 5
    assert result["counts"] == {"0": 2, "1": 3}
    assert result["percentages"]["0"] == pytest.approx(0.4)
    assert result["percentages"]["1"] == pytest.approx(0.6)


def test_calculate_transaction_type_summary_returns_fraud_rates() -> None:
    dataframe = create_sample_cleaned_dataframe()

    result = calculate_transaction_type_summary(
        dataframe=dataframe,
        transaction_type_column="type",
        target_column="isFraud",
    )

    assert result["TRANSFER"]["total_transactions"] == 2
    assert result["TRANSFER"]["fraud_transactions"] == 2
    assert result["TRANSFER"]["fraud_rate"] == pytest.approx(1.0)

    assert result["PAYMENT"]["total_transactions"] == 1
    assert result["PAYMENT"]["fraud_transactions"] == 0
    assert result["PAYMENT"]["fraud_rate"] == pytest.approx(0.0)


def test_calculate_numeric_feature_summary_returns_stats_by_class() -> None:
    dataframe = create_sample_cleaned_dataframe()

    result = calculate_numeric_feature_summary(
        dataframe=dataframe,
        numeric_columns=["amount", "origin_balance_delta"],
        target_column="isFraud",
    )

    assert result["amount"]["0"]["count"] == 2
    assert result["amount"]["1"]["count"] == 3
    assert result["amount"]["1"]["mean"] == pytest.approx((1000.0 + 800.0 + 700.0) / 3)


def test_calculate_balance_behavior_summary_returns_mean_rates() -> None:
    dataframe = create_sample_cleaned_dataframe()

    result = calculate_balance_behavior_summary(
        dataframe=dataframe,
        target_column="isFraud",
    )

    assert result["is_origin_balance_emptied"]["0"] == pytest.approx(0.5)
    assert result["is_origin_balance_emptied"]["1"] == pytest.approx(1.0)
    assert result["is_transfer_type"]["1"] == pytest.approx(2 / 3)


def test_create_eda_summary_contains_expected_sections() -> None:
    dataframe = create_sample_cleaned_dataframe()

    result = create_eda_summary(
        dataframe=dataframe,
        target_column="isFraud",
        transaction_type_column="type",
    )

    expected_sections = {
        "dataset_shape",
        "class_distribution",
        "transaction_type_summary",
        "numeric_feature_summary_by_class",
        "balance_behavior_summary",
    }

    assert expected_sections.issubset(set(result.keys()))