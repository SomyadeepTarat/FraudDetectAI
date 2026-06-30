import json
from pathlib import Path
from typing import Any, cast

import pandas as pd
from sklearn.model_selection import train_test_split

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def validate_feature_columns(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
) -> None:

    required_columns = set(feature_columns + [target_column])
    missing_columns = sorted(required_columns - set(dataframe.columns))

    if missing_columns:
        raise ValueError(f"Missing required columns for modeling: {missing_columns}")


def build_feature_target_matrices(
    dataframe: pd.DataFrame,
    numeric_features: list[str],
    categorical_features: list[str],
    target_column: str,
) -> tuple[pd.DataFrame, pd.Series]:

    feature_columns = numeric_features + categorical_features

    validate_feature_columns(
        dataframe=dataframe,
        feature_columns=feature_columns,
        target_column=target_column,
    )

    X = dataframe[feature_columns].copy()
    y = dataframe[target_column].astype("int64").copy()

    return X, y


def stratified_sample_dataframe(
    dataframe: pd.DataFrame,
    target_column: str,
    max_rows: int | None,
    random_seed: int,
) -> pd.DataFrame:

    if target_column not in dataframe.columns:
        raise ValueError(f"Target column not found: {target_column}")

    if max_rows is None or max_rows <= 0 or len(dataframe) <= max_rows:
        return dataframe.copy()

    class_counts = dataframe[target_column].value_counts()

    if len(class_counts) < 2:
        logger.warning(
            "Target column has fewer than two classes. Falling back to random sample."
        )
        return dataframe.sample(n=max_rows, random_state=random_seed).copy()

    sampled_parts: list[pd.DataFrame] = []

    for class_value, class_count in class_counts.items():
        class_dataframe = dataframe[dataframe[target_column] == class_value]

        class_fraction = class_count / len(dataframe)
        class_sample_size = max(1, int(round(max_rows * class_fraction)))
        class_sample_size = min(class_sample_size, len(class_dataframe))

        sampled_class_dataframe = class_dataframe.sample(
            n=class_sample_size,
            random_state=random_seed,
        )

        sampled_parts.append(sampled_class_dataframe)

    sampled_dataframe = pd.concat(sampled_parts, axis=0)

    if len(sampled_dataframe) > max_rows:
        sampled_dataframe = sampled_dataframe.sample(
            n=max_rows,
            random_state=random_seed,
        )

    sampled_dataframe = sampled_dataframe.sample(
        frac=1.0,
        random_state=random_seed,
    ).reset_index(drop=True)

    logger.info(
        "Sampled dataframe from %s rows to %s rows.",
        len(dataframe),
        len(sampled_dataframe),
    )

    return sampled_dataframe


def create_train_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float,
    random_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:

    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")

    split_result = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_seed,
        stratify=y,
    )

    return cast(
        tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series],
        split_result,
    )


def save_feature_columns(
    numeric_features: list[str],
    categorical_features: list[str],
    output_path: str | Path,
) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    payload: dict[str, Any] = {
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "all_features": numeric_features + categorical_features,
    }

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    logger.info("Saved feature columns to: %s", resolved_output_path)

    return resolved_output_path