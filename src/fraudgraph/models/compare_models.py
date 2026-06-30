import json
from pathlib import Path
from typing import Any

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir, resolve_project_path

logger = get_logger(__name__)


IMPORTANT_METRICS = [
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "average_precision",
]


def load_metrics_report(metrics_path: str | Path) -> dict[str, Any]:
    
    resolved_metrics_path = resolve_project_path(metrics_path)

    if not resolved_metrics_path.exists():
        raise FileNotFoundError(f"Metrics report not found: {resolved_metrics_path}")

    with resolved_metrics_path.open("r", encoding="utf-8") as file:
        metrics_report = json.load(file)

    if "models" not in metrics_report:
        raise ValueError(f"Metrics report does not contain 'models': {resolved_metrics_path}")

    return metrics_report


def calculate_metric_delta(
    baseline_value: float,
    graph_value: float,
) -> dict[str, float]:

    absolute_delta = graph_value - baseline_value

    if baseline_value == 0:
        relative_delta_percent = 0.0 if graph_value == 0 else 100.0
    else:
        relative_delta_percent = (absolute_delta / baseline_value) * 100

    return {
        "baseline": float(baseline_value),
        "graph_enhanced": float(graph_value),
        "absolute_delta": float(absolute_delta),
        "relative_delta_percent": float(relative_delta_percent),
    }


def compare_single_model_metrics(
    baseline_metrics: dict[str, Any],
    graph_metrics: dict[str, Any],
    metric_names: list[str],
) -> dict[str, Any]:

    comparison: dict[str, Any] = {}

    for metric_name in metric_names:
        if metric_name not in baseline_metrics:
            raise ValueError(f"Baseline metrics missing metric: {metric_name}")

        if metric_name not in graph_metrics:
            raise ValueError(f"Graph metrics missing metric: {metric_name}")

        comparison[metric_name] = calculate_metric_delta(
            baseline_value=float(baseline_metrics[metric_name]),
            graph_value=float(graph_metrics[metric_name]),
        )

    return comparison


def compare_model_reports(
    baseline_report: dict[str, Any],
    graph_report: dict[str, Any],
    metric_names: list[str] | None = None,
) -> dict[str, Any]:

    selected_metrics = metric_names if metric_names is not None else IMPORTANT_METRICS

    baseline_models = baseline_report.get("models", {})
    graph_models = graph_report.get("models", {})

    common_model_names = sorted(set(baseline_models) & set(graph_models))

    if not common_model_names:
        raise ValueError("No common model names found between reports.")

    comparison_by_model: dict[str, Any] = {}

    for model_name in common_model_names:
        comparison_by_model[model_name] = compare_single_model_metrics(
            baseline_metrics=baseline_models[model_name],
            graph_metrics=graph_models[model_name],
            metric_names=selected_metrics,
        )

    best_baseline_model = find_best_model_by_metric(
        metrics_report=baseline_report,
        metric_name="average_precision",
    )

    best_graph_model = find_best_model_by_metric(
        metrics_report=graph_report,
        metric_name="average_precision",
    )

    comparison_report = {
        "comparison_basis": {
            "metric_names": selected_metrics,
            "primary_selection_metric": "average_precision",
        },
        "common_models": common_model_names,
        "best_baseline_model_by_average_precision": best_baseline_model,
        "best_graph_model_by_average_precision": best_graph_model,
        "model_comparisons": comparison_by_model,
    }

    return comparison_report


def find_best_model_by_metric(
    metrics_report: dict[str, Any],
    metric_name: str,
) -> dict[str, Any]:

    models = metrics_report.get("models", {})

    if not models:
        raise ValueError("Metrics report contains no models.")

    best_model_name = None
    best_score = float("-inf")

    for model_name, model_metrics in models.items():
        if metric_name not in model_metrics:
            raise ValueError(
                f"Model '{model_name}' does not contain metric '{metric_name}'."
            )

        score = float(model_metrics[metric_name])

        if score > best_score:
            best_score = score
            best_model_name = model_name

    if best_model_name is None:
        raise ValueError(f"Could not find best model by metric: {metric_name}")

    return {
        "model_name": best_model_name,
        "metric_name": metric_name,
        "score": float(best_score),
    }


def save_comparison_report(
    comparison_report: dict[str, Any],
    output_path: str | Path,
) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(comparison_report, file, indent=2)

    logger.info("Saved comparison report to: %s", resolved_output_path)

    return resolved_output_path