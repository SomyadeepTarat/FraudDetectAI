import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def get_positive_class_scores(model: Any, X: pd.DataFrame) -> np.ndarray:

    if hasattr(model, "predict_proba"):
        probability_matrix = model.predict_proba(X)

        if probability_matrix.shape[1] < 2:
            raise ValueError("predict_proba output does not contain two classes.")

        return probability_matrix[:, 1]

    if hasattr(model, "decision_function"):
        decision_scores = model.decision_function(X)
        return np.asarray(decision_scores)

    raise ValueError(
        "Model must support either predict_proba or decision_function for scoring."
    )


def evaluate_binary_classifier(
    model: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    threshold: float = 0.5,
) -> dict[str, Any]:

    if not 0 < threshold < 1:
        raise ValueError("threshold must be between 0 and 1.")

    y_scores = get_positive_class_scores(model, X_test)
    y_pred = (y_scores >= threshold).astype(int)

    labels = [0, 1]
    cm = confusion_matrix(y_test, y_pred, labels=labels)

    tn, fp, fn, tp = cm.ravel()

    metrics = {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(
            precision_score(y_test, y_pred, zero_division=0)
        ),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_scores)),
        "average_precision": float(average_precision_score(y_test, y_scores)),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
    }

    return metrics


def save_metrics_report(
    metrics_report: dict[str, Any],
    output_path: str | Path,
) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(metrics_report, file, indent=2)

    logger.info("Saved metrics report to: %s", resolved_output_path)

    return resolved_output_path


def plot_confusion_matrices(
    metrics_report: dict[str, Any],
    output_path: str | Path,
) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    model_names = list(metrics_report["models"].keys())
    num_models = len(model_names)

    if num_models == 0:
        raise ValueError("No model metrics found to plot.")

    figure_width = max(6, 5 * num_models)
    plt.figure(figsize=(figure_width, 4))

    for index, model_name in enumerate(model_names, start=1):
        model_metrics = metrics_report["models"][model_name]
        cm_values = model_metrics["confusion_matrix"]

        matrix = np.array(
            [
                [
                    cm_values["true_negative"],
                    cm_values["false_positive"],
                ],
                [
                    cm_values["false_negative"],
                    cm_values["true_positive"],
                ],
            ]
        )

        plt.subplot(1, num_models, index)
        image = plt.imshow(matrix, aspect="auto")
        plt.colorbar(image)
        plt.title(model_name.replace("_", " ").title())
        plt.xlabel("Predicted Label")
        plt.ylabel("True Label")
        plt.xticks([0, 1], ["Non-Fraud", "Fraud"], rotation=30, ha="right")
        plt.yticks([0, 1], ["Non-Fraud", "Fraud"])

        for row_index in range(matrix.shape[0]):
            for column_index in range(matrix.shape[1]):
                plt.text(
                    column_index,
                    row_index,
                    str(matrix[row_index, column_index]),
                    ha="center",
                    va="center",
                )

    plt.tight_layout()
    plt.savefig(resolved_output_path, dpi=150)
    plt.close()

    logger.info("Saved confusion matrix figure to: %s", resolved_output_path)

    return resolved_output_path