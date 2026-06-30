import pandas as pd
import pytest

from fraudgraph.features.transaction_features import (
    build_feature_target_matrices,
    create_train_test_split,
    stratified_sample_dataframe,
    validate_feature_columns,
)


def create_sample_modeling_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "step": list(range(10)),
            "type": [
                "PAYMENT",
                "TRANSFER",
                "CASH_OUT",
                "PAYMENT",
                "TRANSFER",
                "CASH_OUT",
                "PAYMENT",
                "TRANSFER",
                "CASH_OUT",
                "PAYMENT",
            ],
            "amount": [
                100.0,
                500.0,
                700.0,
                120.0,
                900.0,
                400.0,
                150.0,
                1000.0,
                650.0,
                110.0,
            ],
            "oldbalanceOrg": [
                1000.0,
                500.0,
                700.0,
                1200.0,
                900.0,
                400.0,
                1500.0,
                1000.0,
                650.0,
                1100.0,
            ],
            "newbalanceOrig": [
                900.0,
                0.0,
                0.0,
                1080.0,
                0.0,
                0.0,
                1350.0,
                0.0,
                0.0,
                990.0,
            ],
            "oldbalanceDest": [
                0.0,
                100.0,
                200.0,
                0.0,
                300.0,
                150.0,
                0.0,
                500.0,
                250.0,
                0.0,
            ],
            "newbalanceDest": [
                0.0,
                600.0,
                900.0,
                0.0,
                1200.0,
                550.0,
                0.0,
                1500.0,
                900.0,
                0.0,
            ],
            "origin_balance_delta": [
                100.0,
                500.0,
                700.0,
                120.0,
                900.0,
                400.0,
                150.0,
                1000.0,
                650.0,
                110.0,
            ],
            "destination_balance_delta": [
                0.0,
                500.0,
                700.0,
                0.0,
                900.0,
                400.0,
                0.0,
                1000.0,
                650.0,
                0.0,
            ],
            "amount_to_old_origin_balance_ratio": [
                0.1,
                1.0,
                1.0,
                0.1,
                1.0,
                1.0,
                0.1,
                1.0,
                1.0,
                0.1,
            ],
            "amount_to_old_destination_balance_ratio": [
                100000000000.0,
                5.0,
                3.5,
                120000000000.0,
                3.0,
                2.6,
                150000000000.0,
                2.0,
                2.6,
                110000000000.0,
            ],
            "is_origin_balance_emptied": [0, 1, 1, 0, 1, 1, 0, 1, 1, 0],
            "is_destination_balance_unchanged": [1, 0, 0, 1, 0, 0, 1, 0, 0, 1],
            "is_transfer_type": [0, 1, 0, 0, 1, 0, 0, 1, 0, 0],
            "is_cashout_type": [0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
            "isFraud": [0, 1, 1, 0, 1, 1, 0, 1, 1, 0],
        }
    )


def test_validate_feature_columns_passes_when_columns_exist() -> None:
    dataframe = create_sample_modeling_dataframe()

    validate_feature_columns(
        dataframe=dataframe,
        feature_columns=["step", "amount", "type"],
        target_column="isFraud",
    )


def test_validate_feature_columns_raises_when_column_missing() -> None:
    dataframe = create_sample_modeling_dataframe()

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_feature_columns(
            dataframe=dataframe,
            feature_columns=["step", "missing_feature", "type"],
            target_column="isFraud",
        )


def test_build_feature_target_matrices_returns_expected_shapes() -> None:
    dataframe = create_sample_modeling_dataframe()

    X, y = build_feature_target_matrices(
        dataframe=dataframe,
        numeric_features=["step", "amount"],
        categorical_features=["type"],
        target_column="isFraud",
    )

    assert X.shape == (10, 3)
    assert y.shape == (10,)
    assert y.dtype == "int64"


def test_stratified_sample_dataframe_returns_requested_size() -> None:
    dataframe = create_sample_modeling_dataframe()

    sampled_dataframe = stratified_sample_dataframe(
        dataframe=dataframe,
        target_column="isFraud",
        max_rows=6,
        random_seed=42,
    )

    assert len(sampled_dataframe) == 6
    assert set(sampled_dataframe["isFraud"].unique()) == {0, 1}


def test_stratified_sample_dataframe_returns_full_dataframe_when_small() -> None:
    dataframe = create_sample_modeling_dataframe()

    sampled_dataframe = stratified_sample_dataframe(
        dataframe=dataframe,
        target_column="isFraud",
        max_rows=100,
        random_seed=42,
    )

    assert len(sampled_dataframe) == len(dataframe)


def test_create_train_test_split_preserves_shapes() -> None:
    dataframe = create_sample_modeling_dataframe()

    X, y = build_feature_target_matrices(
        dataframe=dataframe,
        numeric_features=["step", "amount"],
        categorical_features=["type"],
        target_column="isFraud",
    )

    X_train, X_test, y_train, y_test = create_train_test_split(
        X=X,
        y=y,
        test_size=0.3,
        random_seed=42,
    )

    assert len(X_train) == 7
    assert len(X_test) == 3
    assert len(y_train) == 7
    assert len(y_test) == 3