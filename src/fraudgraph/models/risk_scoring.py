import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fraudgraph.models.evaluate import get_positive_class_scores
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def assign_risk_band(
    fraud_probability: float,
    low_max: float,
    medium_max: float,
    high_max: float,
) -> str:

    if not 0 <= fraud_probability <= 1:
        raise ValueError("fraud_probability must be between 0 and 1.")

    if not 0 < low_max < medium_max < high_max < 1:
        raise ValueError("Risk band cutoffs must satisfy 0 < low < medium < high < 1.")

    if fraud_probability < low_max:
        return "LOW"

    if fraud_probability < medium_max:
        return "MEDIUM"

    if fraud_probability < high_max:
        return "HIGH"

    return "CRITICAL"


def score_transactions(
    model: Any,
    dataframe: pd.DataFrame,
    feature_columns: list[str],
    decision_threshold: float,
    risk_band_config: dict[str, float],
) -> pd.DataFrame:

    missing_columns = sorted(set(feature_columns) - set(dataframe.columns))

    if missing_columns:
        raise ValueError(f"Missing feature columns for scoring: {missing_columns}")

    if not 0 < decision_threshold < 1:
        raise ValueError("decision_threshold must be between 0 and 1.")

    X = dataframe[feature_columns].copy()

    fraud_probabilities = get_positive_class_scores(model, X)
    predicted_fraud = (fraud_probabilities >= decision_threshold).astype(int)

    scored_dataframe = dataframe.copy()
    scored_dataframe["fraud_probability"] = fraud_probabilities
    scored_dataframe["predicted_fraud"] = predicted_fraud
    scored_dataframe["risk_band"] = [
        assign_risk_band(
            fraud_probability=float(probability),
            low_max=float(risk_band_config["low_max"]),
            medium_max=float(risk_band_config["medium_max"]),
            high_max=float(risk_band_config["high_max"]),
        )
        for probability in fraud_probabilities
    ]

    scored_dataframe = scored_dataframe.sort_values(
        by="fraud_probability",
        ascending=False,
    ).reset_index(drop=True)

    return scored_dataframe


def create_risk_scoring_report(
    scored_dataframe: pd.DataFrame,
    target_column: str,
    decision_threshold: float,
) -> dict[str, Any]:

    required_columns = {
        "fraud_probability",
        "predicted_fraud",
        "risk_band",
        target_column,
    }

    missing_columns = sorted(required_columns - set(scored_dataframe.columns))

    if missing_columns:
        raise ValueError(f"Missing required scoring report columns: {missing_columns}")

    risk_band_counts = scored_dataframe["risk_band"].value_counts().to_dict()
    predicted_counts = scored_dataframe["predicted_fraud"].value_counts().to_dict()

    report = {
        "decision_threshold": float(decision_threshold),
        "num_transactions_scored": int(len(scored_dataframe)),
        "risk_band_counts": {
            str(key): int(value)
            for key, value in risk_band_counts.items()
        },
        "predicted_fraud_counts": {
            str(key): int(value)
            for key, value in predicted_counts.items()
        },
        "average_fraud_probability": float(scored_dataframe["fraud_probability"].mean()),
        "max_fraud_probability": float(scored_dataframe["fraud_probability"].max()),
        "min_fraud_probability": float(scored_dataframe["fraud_probability"].min()),
        "actual_fraud_rate_by_risk_band": {},
    }

    grouped = scored_dataframe.groupby("risk_band", observed=True)[target_column]

    for risk_band, labels in grouped:
        report["actual_fraud_rate_by_risk_band"][str(risk_band)] = float(labels.mean())

    return report


def save_scored_transactions(
    scored_dataframe: pd.DataFrame,
    output_path: str | Path,
) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    scored_dataframe.to_parquet(resolved_output_path, index=False)

    logger.info("Saved scored transactions to: %s", resolved_output_path)

    return resolved_output_path


def save_risk_scoring_report(
    report: dict[str, Any],
    output_path: str | Path,
) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    logger.info("Saved risk scoring report to: %s", resolved_output_path)

    return resolved_output_path


def get_top_risky_transactions(
    scored_dataframe: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:

    if top_n <= 0:
        raise ValueError("top_n must be greater than 0.")

    if "fraud_probability" not in scored_dataframe.columns:
        raise ValueError("scored_dataframe must contain fraud_probability column.")

    return scored_dataframe.sort_values(
        by="fraud_probability",
        ascending=False,
    ).head(top_n)