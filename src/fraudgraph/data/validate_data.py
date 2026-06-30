import json
from pathlib import Path
from typing import Any

import pandas as pd

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def check_required_columns(
    dataframe: pd.DataFrame,
    required_columns: list[str],
) -> list[str]:
    existing_columns = set(dataframe.columns)
    missing_columns = [
        column for column in required_columns if column not in existing_columns
    ]
    return missing_columns


def check_numeric_columns(
    dataframe: pd.DataFrame,
    numeric_columns: list[str],
) -> dict[str, str]:
    invalid_columns: dict[str, str] = {}

    for column in numeric_columns:
        if column in dataframe.columns and not pd.api.types.is_numeric_dtype(
            dataframe[column]
        ):
            invalid_columns[column] = str(dataframe[column].dtype)

    return invalid_columns


def check_binary_target(
    dataframe: pd.DataFrame,
    target_column: str,
    allowed_values: set[int],
) -> dict[str, Any]:
    if target_column not in dataframe.columns:
        return {
            "exists": False,
            "valid": False,
            "unique_values": [],
            "invalid_values": [],
        }

    unique_values = sorted(dataframe[target_column].dropna().unique().tolist())
    unique_value_set = set(unique_values)
    invalid_values = sorted(list(unique_value_set - allowed_values))

    return {
        "exists": True,
        "valid": len(invalid_values) == 0,
        "unique_values": unique_values,
        "invalid_values": invalid_values,
    }


def summarize_missing_values(dataframe: pd.DataFrame) -> dict[str, int]:
    missing_counts = dataframe.isna().sum()
    return {
        str(column): int(count)
        for column, count in missing_counts.items()
        if int(count) > 0
    }


def summarize_target_distribution(
    dataframe: pd.DataFrame,
    target_column: str,
) -> dict[str, Any]:
    if target_column not in dataframe.columns:
        return {
            "target_column": target_column,
            "exists": False,
            "counts": {},
            "positive_rate": None,
        }

    counts = dataframe[target_column].value_counts(dropna=False).to_dict()
    formatted_counts = {str(key): int(value) for key, value in counts.items()}

    positive_count = int((dataframe[target_column] == 1).sum())
    total_count = int(len(dataframe))
    positive_rate = positive_count / total_count if total_count > 0 else 0.0

    return {
        "target_column": target_column,
        "exists": True,
        "counts": formatted_counts,
        "positive_rate": positive_rate,
    }


def create_validation_report(
    dataframe: pd.DataFrame,
    required_columns: list[str],
    numeric_columns: list[str],
    target_column: str,
) -> dict[str, Any]:
    missing_required_columns = check_required_columns(dataframe, required_columns)
    invalid_numeric_columns = check_numeric_columns(dataframe, numeric_columns)
    target_check = check_binary_target(
        dataframe=dataframe,
        target_column=target_column,
        allowed_values={0, 1},
    )
    missing_values = summarize_missing_values(dataframe)
    target_distribution = summarize_target_distribution(dataframe, target_column)

    is_valid = (
        len(missing_required_columns) == 0
        and len(invalid_numeric_columns) == 0
        and target_check["valid"]
    )

    report = {
        "is_valid": is_valid,
        "num_rows": int(dataframe.shape[0]),
        "num_columns": int(dataframe.shape[1]),
        "columns": list(dataframe.columns),
        "missing_required_columns": missing_required_columns,
        "invalid_numeric_columns": invalid_numeric_columns,
        "target_check": target_check,
        "missing_values": missing_values,
        "target_distribution": target_distribution,
    }

    return report


def save_validation_report(
    report: dict[str, Any],
    output_path: str | Path,
) -> Path:
    resolved_output_path = ensure_parent_dir(output_path)

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    logger.info("Saved validation report to: %s", resolved_output_path)

    return resolved_output_path


def assert_valid_dataset(report: dict[str, Any]) -> None:
    if report["is_valid"]:
        return

    error_messages: list[str] = []

    missing_columns = report.get("missing_required_columns", [])
    if missing_columns:
        error_messages.append(f"Missing required columns: {missing_columns}")

    invalid_numeric_columns = report.get("invalid_numeric_columns", {})
    if invalid_numeric_columns:
        error_messages.append(
            f"Invalid numeric columns: {invalid_numeric_columns}"
        )

    target_check = report.get("target_check", {})
    if not target_check.get("valid", False):
        error_messages.append(f"Invalid target column: {target_check}")

    full_error_message = "Dataset validation failed. " + " | ".join(error_messages)
    raise ValueError(full_error_message)