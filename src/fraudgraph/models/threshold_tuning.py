import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def generate_thresholds(
    threshold_min: float,
    threshold_max: float, 
    threshold_step: float,
) -> list[float]:

    if not 0 < threshold_min < 1:
        raise ValueError("threshold_min must be between 0 and 1.")

    if not 0 < threshold_max < 1:
        raise ValueError("threshold_max must be between 0 and 1.")

    if threshold_min >= threshold_max:
        raise ValueError("threshold_min must be smaller than threshold_max.")

    if threshold_step <= 0:
        raise ValueError("threshold_step must be greater than 0.")

    thresholds: list[float] = []
    current_threshold = threshold_min

    while current_threshold <= threshold_max + 1e-12:
        thresholds.append(round(float(current_threshold), 6))
        current_threshold += threshold_step

    return thresholds


def calculate_metrics_at_threshold(
    y_true: pd.Series | np.ndarray,
    y_scores: np.ndarray,
    threshold: float,
) -> dict[str, Any]:

    if not 0 < threshold < 1:
        raise ValueError("threshold must be between 0 and 1.")

    y_pred = (y_scores >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    ).ravel()

    metrics = {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }

    return metrics


def evaluate_thresholds(
    y_true: pd.Series | np.ndarray,
    y_scores: np.ndarray,
    thresholds: list[float],
) -> pd.DataFrame:

    if len(thresholds) == 0:
        raise ValueError("thresholds cannot be empty.")

    rows = [
        calculate_metrics_at_threshold(
            y_true=y_true,
            y_scores=y_scores,
            threshold=threshold,
        )
        for threshold in thresholds
    ]

    return pd.DataFrame(rows)


def select_best_threshold(
    threshold_results: pd.DataFrame,
    optimization_metric: str,
    minimum_recall: float | None = None,
) -> dict[str, Any]:

    if optimization_metric not in threshold_results.columns:
        raise ValueError(f"Metric not found in threshold results: {optimization_metric}")

    candidate_results = threshold_results.copy()

    if minimum_recall is not None:
        if not 0 <= minimum_recall <= 1:
            raise ValueError("minimum_recall must be between 0 and 1.")

        candidate_results = candidate_results[
            candidate_results["recall"] >= minimum_recall
        ]

    if candidate_results.empty:
        raise ValueError(
            "No threshold satisfies the requested minimum recall constraint."
        )

    sorted_results = candidate_results.sort_values(
        by=[optimization_metric, "precision", "recall"],
        ascending=[False, False, False],
    )

    best_row = sorted_results.iloc[0].to_dict()

    return {
        str(key): float(value) if isinstance(value, (np.floating, float)) else int(value)
        if isinstance(value, (np.integer, int))
        else value
        for key, value in best_row.items()
    }


def create_threshold_tuning_report(
    threshold_results: pd.DataFrame,
    best_threshold_result: dict[str, Any],
    optimization_metric: str,
    minimum_recall: float | None,
    model_name: str,
) -> dict[str, Any]:

    return {
        "model_name": model_name,
        "optimization_metric": optimization_metric,
        "minimum_recall": minimum_recall,
        "best_threshold": best_threshold_result,
        "num_thresholds_evaluated": int(len(threshold_results)),
        "threshold_results": threshold_results.to_dict(orient="records"),
    }


def save_threshold_tuning_report(
    report: dict[str, Any],
    output_path: str | Path,
) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    logger.info("Saved threshold tuning report to: %s", resolved_output_path)

    return resolved_output_path


def save_threshold_curve_plot(
    threshold_results: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    
    required_columns = {"threshold", "precision", "recall", "f1"}
    missing_columns = required_columns - set(threshold_results.columns)

    if missing_columns:
        raise ValueError(f"Missing threshold result columns: {missing_columns}")

    resolved_output_path = ensure_parent_dir(output_path)

    plt.figure(figsize=(10, 6))
    plt.plot(threshold_results["threshold"], threshold_results["precision"], label="Precision")
    plt.plot(threshold_results["threshold"], threshold_results["recall"], label="Recall")
    plt.plot(threshold_results["threshold"], threshold_results["f1"], label="F1")
    plt.title("Threshold Tuning: Precision, Recall, and F1")
    plt.xlabel("Decision Threshold")
    plt.ylabel("Metric Value")
    plt.legend()
    plt.tight_layout()
    plt.savefig(resolved_output_path, dpi=150)
    plt.close()

    logger.info("Saved threshold tuning curve to: %s", resolved_output_path)

    return resolved_output_path