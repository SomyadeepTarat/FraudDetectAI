from pathlib import Path

import pandas as pd

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


TRANSACTION_TYPE_COLUMN = "type"
TARGET_COLUMN = "isFraud"


def standardize_column_names(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned_dataframe = dataframe.copy()
    cleaned_dataframe.columns = [column.strip() for column in cleaned_dataframe.columns]
    return cleaned_dataframe


def remove_duplicate_rows(dataframe: pd.DataFrame) -> pd.DataFrame:
    initial_rows = len(dataframe)
    cleaned_dataframe = dataframe.drop_duplicates().copy()
    removed_rows = initial_rows - len(cleaned_dataframe)

    logger.info("Removed %s duplicate rows.", removed_rows)

    return cleaned_dataframe


def enforce_expected_dtypes(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned_dataframe = dataframe.copy()

    integer_columns = ["step", "isFraud", "isFlaggedFraud"]
    float_columns = [
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
    ]
    string_columns = ["type", "nameOrig", "nameDest"]

    for column in integer_columns:
        if column in cleaned_dataframe.columns:
            cleaned_dataframe[column] = cleaned_dataframe[column].astype("int64")

    for column in float_columns:
        if column in cleaned_dataframe.columns:
            cleaned_dataframe[column] = cleaned_dataframe[column].astype("float64")

    for column in string_columns:
        if column in cleaned_dataframe.columns:
            cleaned_dataframe[column] = cleaned_dataframe[column].astype("string")

    return cleaned_dataframe


def create_basic_transaction_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned_dataframe = dataframe.copy()

    epsilon = 1e-9

    cleaned_dataframe["origin_balance_delta"] = (
        cleaned_dataframe["oldbalanceOrg"] - cleaned_dataframe["newbalanceOrig"]
    )

    cleaned_dataframe["destination_balance_delta"] = (
        cleaned_dataframe["newbalanceDest"] - cleaned_dataframe["oldbalanceDest"]
    )

    cleaned_dataframe["amount_to_old_origin_balance_ratio"] = (
        cleaned_dataframe["amount"] / (cleaned_dataframe["oldbalanceOrg"] + epsilon)
    )

    cleaned_dataframe["amount_to_old_destination_balance_ratio"] = (
        cleaned_dataframe["amount"] / (cleaned_dataframe["oldbalanceDest"] + epsilon)
    )

    cleaned_dataframe["is_origin_balance_emptied"] = (
        (cleaned_dataframe["oldbalanceOrg"] > 0)
        & (cleaned_dataframe["newbalanceOrig"] == 0)
    ).astype("int64")

    cleaned_dataframe["is_destination_balance_unchanged"] = (
        cleaned_dataframe["oldbalanceDest"] == cleaned_dataframe["newbalanceDest"]
    ).astype("int64")

    cleaned_dataframe["is_transfer_type"] = (
        cleaned_dataframe[TRANSACTION_TYPE_COLUMN] == "TRANSFER"
    ).astype("int64")

    cleaned_dataframe["is_cashout_type"] = (
        cleaned_dataframe[TRANSACTION_TYPE_COLUMN] == "CASH_OUT"
    ).astype("int64")

    return cleaned_dataframe


def clean_paysim_data(
    dataframe: pd.DataFrame,
    drop_duplicates: bool = True,
) -> pd.DataFrame:
    logger.info("Starting PaySim preprocessing.")

    cleaned_dataframe = standardize_column_names(dataframe)

    if drop_duplicates:
        cleaned_dataframe = remove_duplicate_rows(cleaned_dataframe)

    cleaned_dataframe = enforce_expected_dtypes(cleaned_dataframe)
    cleaned_dataframe = create_basic_transaction_features(cleaned_dataframe)

    logger.info("Finished preprocessing. Cleaned shape: %s", cleaned_dataframe.shape)

    return cleaned_dataframe


def save_cleaned_data(
    dataframe: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    resolved_output_path = ensure_parent_dir(output_path)

    dataframe.to_parquet(resolved_output_path, index=False)

    logger.info("Saved cleaned dataset to: %s", resolved_output_path)

    return resolved_output_path