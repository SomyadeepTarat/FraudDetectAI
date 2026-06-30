import json
from pathlib import Path
from typing import Any

import pandas as pd

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def calculate_class_distribution(
    dataframe: pd.DataFrame,
    target_column: str,
) -> dict[str, Any]:
    
    if target_column not in dataframe.columns:
        raise ValueError(f"Target column not found: {target_column}")

    total_rows = int(len(dataframe))
    counts = dataframe[target_column].value_counts().sort_index().to_dict()

    formatted_counts = {str(key): int(value) for key, value in counts.items()}
    percentages = {
        str(key): float(value / total_rows) if total_rows > 0 else 0.0
        for key, value in counts.items()
    }

    return {
        "target_column": target_column,
        "total_rows": total_rows,
        "counts": formatted_counts,
        "percentages": percentages,
    }


def calculate_transaction_type_summary(
    dataframe: pd.DataFrame,
    transaction_type_column: str,
    target_column: str,
) -> dict[str, Any]:

    required_columns = {transaction_type_column, target_column}
    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(f"Missing columns for transaction summary: {missing_columns}")

    grouped = (
        dataframe.groupby(transaction_type_column, observed=True)
        .agg(
            total_transactions=(target_column, "count"),
            fraud_transactions=(target_column, "sum"),
        )
        .reset_index()
    )

    grouped["fraud_rate"] = (
        grouped["fraud_transactions"] / grouped["total_transactions"]
    )

    grouped = grouped.sort_values(
        by=["fraud_rate", "fraud_transactions"],
        ascending=[False, False],
    )

    summary: dict[str, Any] = {}

    for row in grouped.to_dict(orient="records"):
        transaction_type = str(row[transaction_type_column])
        summary[transaction_type] = {
            "total_transactions": int(row["total_transactions"]),
            "fraud_transactions": int(row["fraud_transactions"]),
            "fraud_rate": float(row["fraud_rate"]),
        }

    return summary


def calculate_numeric_feature_summary(
    dataframe: pd.DataFrame,
    numeric_columns: list[str],
    target_column: str,
) -> dict[str, Any]:

    if target_column not in dataframe.columns:
        raise ValueError(f"Target column not found: {target_column}")

    existing_numeric_columns = [
        column for column in numeric_columns if column in dataframe.columns
    ]

    if not existing_numeric_columns:
        raise ValueError("No requested numeric columns were found in the dataframe.")

    summary: dict[str, Any] = {}

    for column in existing_numeric_columns:
        column_summary: dict[str, Any] = {}

        grouped = dataframe.groupby(target_column, observed=True)[column]

        for class_value, series in grouped:
            clean_series = series.dropna()

            if clean_series.empty:
                column_summary[str(class_value)] = {
                    "count": 0,
                    "mean": None,
                    "median": None,
                    "std": None,
                    "min": None,
                    "max": None,
                }
            else:
                column_summary[str(class_value)] = {
                    "count": int(clean_series.count()),
                    "mean": float(clean_series.mean()),
                    "median": float(clean_series.median()),
                    "std": float(clean_series.std())
                    if clean_series.count() > 1
                    else 0.0,
                    "min": float(clean_series.min()),
                    "max": float(clean_series.max()),
                }

        summary[column] = column_summary

    return summary


def calculate_balance_behavior_summary(
    dataframe: pd.DataFrame,
    target_column: str,
) -> dict[str, Any]:

    required_columns = {
        target_column,
        "is_origin_balance_emptied",
        "is_destination_balance_unchanged",
        "is_transfer_type",
        "is_cashout_type",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(f"Missing columns for balance behavior summary: {missing_columns}")

    behavior_columns = [
        "is_origin_balance_emptied",
        "is_destination_balance_unchanged",
        "is_transfer_type",
        "is_cashout_type",
    ]

    summary: dict[str, Any] = {}

    for behavior_column in behavior_columns:
        grouped = dataframe.groupby(target_column, observed=True)[behavior_column].mean()
        summary[behavior_column] = {
            str(class_value): float(rate)
            for class_value, rate in grouped.to_dict().items()
        }

    return summary


def create_eda_summary(
    dataframe: pd.DataFrame,
    target_column: str,
    transaction_type_column: str,
) -> dict[str, Any]:

    numeric_columns = [
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "origin_balance_delta",
        "destination_balance_delta",
        "amount_to_old_origin_balance_ratio",
        "amount_to_old_destination_balance_ratio",
    ]

    summary = {
        "dataset_shape": {
            "num_rows": int(dataframe.shape[0]),
            "num_columns": int(dataframe.shape[1]),
        },
        "class_distribution": calculate_class_distribution(
            dataframe=dataframe,
            target_column=target_column,
        ),
        "transaction_type_summary": calculate_transaction_type_summary(
            dataframe=dataframe,
            transaction_type_column=transaction_type_column,
            target_column=target_column,
        ),
        "numeric_feature_summary_by_class": calculate_numeric_feature_summary(
            dataframe=dataframe,
            numeric_columns=numeric_columns,
            target_column=target_column,
        ),
        "balance_behavior_summary": calculate_balance_behavior_summary(
            dataframe=dataframe,
            target_column=target_column,
        ),
    }

    return summary


def save_eda_summary(
    summary: dict[str, Any],
    output_path: str | Path,
) -> Path:
    
    resolved_output_path = ensure_parent_dir(output_path)

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    logger.info("Saved EDA summary to: %s", resolved_output_path)

    return resolved_output_path