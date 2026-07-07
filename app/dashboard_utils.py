import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_dashboard_path(relative_path: str | Path) -> Path:

    path = Path(relative_path)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def file_exists(relative_path: str | Path) -> bool:

    return resolve_dashboard_path(relative_path).exists()


def load_json_file(relative_path: str | Path) -> dict[str, Any]:

    resolved_path = resolve_dashboard_path(relative_path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"JSON file not found: {resolved_path}")

    with resolved_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {resolved_path}")

    return payload


def load_parquet_file(relative_path: str | Path) -> pd.DataFrame:

    resolved_path = resolve_dashboard_path(relative_path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {resolved_path}")

    return pd.read_parquet(resolved_path)


def format_percentage(value: float | int | None, decimals: int = 2) -> str:

    if value is None:
        return "N/A"

    return f"{float(value) * 100:.{decimals}f}%"


def format_number(value: float | int | None, decimals: int = 2) -> str:

    if value is None:
        return "N/A"

    if isinstance(value, int):
        return f"{value:,}"

    numeric_value = float(value)

    if numeric_value.is_integer():
        return f"{int(numeric_value):,}"

    return f"{numeric_value:,.{decimals}f}"


def extract_model_metric_table(metrics_report: dict[str, Any]) -> pd.DataFrame:

    models = metrics_report.get("models", {})

    rows: list[dict[str, Any]] = []

    for model_name, metrics in models.items():
        rows.append(
            {
                "model": model_name,
                "accuracy": metrics.get("accuracy"),
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "f1": metrics.get("f1"),
                "roc_auc": metrics.get("roc_auc"),
                "average_precision": metrics.get("average_precision"),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "model",
                "accuracy",
                "precision",
                "recall",
                "f1",
                "roc_auc",
                "average_precision",
            ]
        )

    return pd.DataFrame(rows)


def extract_comparison_table(comparison_report: dict[str, Any]) -> pd.DataFrame:

    model_comparisons = comparison_report.get("model_comparisons", {})

    rows: list[dict[str, Any]] = []

    for model_name, metric_comparison in model_comparisons.items():
        for metric_name, values in metric_comparison.items():
            rows.append(
                {
                    "model": model_name,
                    "metric": metric_name,
                    "baseline": values.get("baseline"),
                    "graph_enhanced": values.get("graph_enhanced"),
                    "absolute_delta": values.get("absolute_delta"),
                    "relative_delta_percent": values.get("relative_delta_percent"),
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "model",
                "metric",
                "baseline",
                "graph_enhanced",
                "absolute_delta",
                "relative_delta_percent",
            ]
        )

    return pd.DataFrame(rows)


def get_available_columns(
    dataframe: pd.DataFrame,
    preferred_columns: list[str],
) -> list[str]:

    return [column for column in preferred_columns if column in dataframe.columns]


def filter_transactions(
    dataframe: pd.DataFrame,
    risk_bands: list[str] | None = None,
    predicted_fraud_only: bool = False,
    min_probability: float = 0.0,
    max_rows: int = 100,
) -> pd.DataFrame:

    if not 0 <= min_probability <= 1:
        raise ValueError("min_probability must be between 0 and 1.")

    if max_rows <= 0:
        raise ValueError("max_rows must be greater than 0.")

    filtered = dataframe.copy()

    if risk_bands:
        filtered = filtered[filtered["risk_band"].isin(risk_bands)]

    if predicted_fraud_only:
        filtered = filtered[filtered["predicted_fraud"] == 1]

    if "fraud_probability" in filtered.columns:
        filtered = filtered[filtered["fraud_probability"] >= min_probability]
        filtered = filtered.sort_values(by="fraud_probability", ascending=False)

    return filtered.head(max_rows).reset_index(drop=True)


def summarize_scored_transactions(scored_dataframe: pd.DataFrame) -> dict[str, Any]:

    required_columns = {
        "fraud_probability",
        "predicted_fraud",
        "risk_band",
    }

    missing_columns = required_columns - set(scored_dataframe.columns)

    if missing_columns:
        raise ValueError(f"Missing scored transaction columns: {sorted(missing_columns)}")

    return {
        "num_transactions": int(len(scored_dataframe)),
        "num_predicted_fraud": int((scored_dataframe["predicted_fraud"] == 1).sum()),
        "average_fraud_probability": float(scored_dataframe["fraud_probability"].mean()),
        "max_fraud_probability": float(scored_dataframe["fraud_probability"].max()),
        "risk_band_counts": {
            str(key): int(value)
            for key, value in scored_dataframe["risk_band"].value_counts().to_dict().items()
        },
    }