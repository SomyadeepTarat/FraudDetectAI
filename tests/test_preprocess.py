import pandas as pd

from fraudgraph.data.preprocess import (
    clean_paysim_data,
    create_basic_transaction_features,
    enforce_expected_dtypes,
    remove_duplicate_rows,
    standardize_column_names,
)


def create_sample_raw_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            " step ": [1, 1, 2],
            "type": ["PAYMENT", "PAYMENT", "TRANSFER"],
            "amount": [100.0, 100.0, 500.0],
            "nameOrig": ["C1", "C1", "C2"],
            "oldbalanceOrg": [1000.0, 1000.0, 500.0],
            "newbalanceOrig": [900.0, 900.0, 0.0],
            "nameDest": ["M1", "M1", "C3"],
            "oldbalanceDest": [0.0, 0.0, 100.0],
            "newbalanceDest": [0.0, 0.0, 600.0],
            "isFraud": [0, 0, 1],
            "isFlaggedFraud": [0, 0, 0],
        }
    )


def create_sample_standard_dataframe() -> pd.DataFrame:
    dataframe = create_sample_raw_dataframe()
    dataframe.columns = [column.strip() for column in dataframe.columns]
    return dataframe


def test_standardize_column_names_strips_whitespace() -> None:
    dataframe = create_sample_raw_dataframe()

    cleaned_dataframe = standardize_column_names(dataframe)

    assert "step" in cleaned_dataframe.columns
    assert " step " not in cleaned_dataframe.columns


def test_remove_duplicate_rows_removes_exact_duplicates() -> None:
    dataframe = create_sample_standard_dataframe()

    cleaned_dataframe = remove_duplicate_rows(dataframe)

    assert len(cleaned_dataframe) == 2


def test_enforce_expected_dtypes_converts_columns() -> None:
    dataframe = create_sample_standard_dataframe()

    cleaned_dataframe = enforce_expected_dtypes(dataframe)

    assert str(cleaned_dataframe["step"].dtype) == "int64"
    assert str(cleaned_dataframe["amount"].dtype) == "float64"
    assert str(cleaned_dataframe["type"].dtype) == "string"
    assert str(cleaned_dataframe["isFraud"].dtype) == "int64"


def test_create_basic_transaction_features_adds_expected_columns() -> None:
    dataframe = create_sample_standard_dataframe()

    featured_dataframe = create_basic_transaction_features(dataframe)

    expected_new_columns = {
        "origin_balance_delta",
        "destination_balance_delta",
        "amount_to_old_origin_balance_ratio",
        "amount_to_old_destination_balance_ratio",
        "is_origin_balance_emptied",
        "is_destination_balance_unchanged",
        "is_transfer_type",
        "is_cashout_type",
    }

    assert expected_new_columns.issubset(set(featured_dataframe.columns))


def test_create_basic_transaction_features_calculates_balance_delta() -> None:
    dataframe = create_sample_standard_dataframe()

    featured_dataframe = create_basic_transaction_features(dataframe)

    assert featured_dataframe.loc[0, "origin_balance_delta"] == 100.0
    assert featured_dataframe.loc[2, "origin_balance_delta"] == 500.0
    assert featured_dataframe.loc[2, "destination_balance_delta"] == 500.0


def test_create_basic_transaction_features_detects_emptied_origin_balance() -> None:
    dataframe = create_sample_standard_dataframe()

    featured_dataframe = create_basic_transaction_features(dataframe)

    assert featured_dataframe.loc[0, "is_origin_balance_emptied"] == 0
    assert featured_dataframe.loc[2, "is_origin_balance_emptied"] == 1


def test_clean_paysim_data_removes_duplicates_and_adds_features() -> None:
    dataframe = create_sample_raw_dataframe()

    cleaned_dataframe = clean_paysim_data(dataframe, drop_duplicates=True)

    assert len(cleaned_dataframe) == 2
    assert "origin_balance_delta" in cleaned_dataframe.columns
    assert "is_transfer_type" in cleaned_dataframe.columns