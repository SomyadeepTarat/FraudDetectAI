import pandas as pd

from fraudgraph.features.transaction_features import (
    build_feature_target_matrices,
    create_train_test_split,
    save_feature_columns,
    stratified_sample_dataframe,
)
from fraudgraph.models.compare_models import (
    compare_model_reports,
    load_metrics_report,
    save_comparison_report,
)
from fraudgraph.models.evaluate import plot_confusion_matrices, save_metrics_report
from fraudgraph.models.train_graph_enhanced import (
    build_graph_model_feature_lists,
    train_graph_enhanced_models,
)
from fraudgraph.utils.config import load_yaml_config
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def main() -> None:
    """
    Steps:
        1. Load config.
        2. Load graph-enhanced dataset.
        3. Build transaction + graph feature list.
        4. Optionally sample large dataset.
        5. Build X and y.
        6. Create stratified train/test split.
        7. Train graph-enhanced models.
        8. Save models, metrics, plots, and feature metadata.
        9. Compare graph-enhanced metrics against baseline metrics if available.
    """
    config = load_yaml_config("configs/config.yaml")

    graph_dataset_path = config["graph_features"]["graph_enhanced_dataset_path"]
    target_column = config["target"]["name"]

    transaction_numeric_features = config["modeling"]["numeric_features"]
    categorical_features = config["modeling"]["categorical_features"]
    graph_feature_columns = config["graph_features"]["graph_feature_columns"]

    numeric_features, categorical_features = build_graph_model_feature_lists(
        transaction_numeric_features=transaction_numeric_features,
        graph_feature_columns=graph_feature_columns,
        categorical_features=categorical_features,
    )

    test_size = float(config["graph_modeling"]["test_size"])
    random_seed = int(config["graph_modeling"]["random_seed"])
    max_training_rows = int(config["graph_modeling"]["max_training_rows"])

    graph_metrics_output_path = config["graph_modeling"]["graph_metrics_output_path"]
    graph_confusion_matrix_figure_path = config["graph_modeling"][
        "graph_confusion_matrix_figure_path"
    ]
    graph_feature_columns_output_path = config["graph_modeling"][
        "graph_feature_columns_output_path"
    ]

    baseline_metrics_output_path = config["modeling"]["metrics_output_path"]
    comparison_output_path = config["graph_modeling"]["comparison_output_path"]

    resolved_graph_dataset_path = resolve_project_path(graph_dataset_path)

    if not resolved_graph_dataset_path.exists():
        raise FileNotFoundError(
            f"Graph-enhanced dataset not found at {resolved_graph_dataset_path}. "
            "Run `python scripts/create_graph_features.py` first."
        )

    logger.info("Loading graph-enhanced dataset from: %s", resolved_graph_dataset_path)
    dataframe = pd.read_parquet(resolved_graph_dataset_path)
    logger.info("Loaded graph-enhanced dataset with shape: %s", dataframe.shape)

    sampled_dataframe = stratified_sample_dataframe(
        dataframe=dataframe,
        target_column=target_column,
        max_rows=max_training_rows,
        random_seed=random_seed,
    )

    X, y = build_feature_target_matrices(
        dataframe=sampled_dataframe,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        target_column=target_column,
    )

    logger.info("Graph-enhanced feature matrix shape: %s", X.shape)
    logger.info("Target distribution: %s", y.value_counts().to_dict())

    X_train, X_test, y_train, y_test = create_train_test_split(
        X=X,
        y=y,
        test_size=test_size,
        random_seed=random_seed,
    )

    logger.info("Train shape: %s", X_train.shape)
    logger.info("Test shape: %s", X_test.shape)
    logger.info("Train target distribution: %s", y_train.value_counts().to_dict())
    logger.info("Test target distribution: %s", y_test.value_counts().to_dict())

    save_feature_columns(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        output_path=graph_feature_columns_output_path,
    )

    metrics_by_model = train_graph_enhanced_models(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        config=config,
    )

    metrics_report = {
        "dataset": {
            "source_path": str(resolved_graph_dataset_path),
            "num_rows_used": int(len(sampled_dataframe)),
            "num_features": int(X.shape[1]),
            "test_size": test_size,
            "target_distribution": {
                str(label): int(count)
                for label, count in y.value_counts().to_dict().items()
            },
        },
        "features": {
            "transaction_numeric_features": transaction_numeric_features,
            "graph_feature_columns": graph_feature_columns,
            "all_numeric_features": numeric_features,
            "categorical_features": categorical_features,
        },
        "models": metrics_by_model,
    }

    save_metrics_report(
        metrics_report=metrics_report,
        output_path=graph_metrics_output_path,
    )

    plot_confusion_matrices(
        metrics_report=metrics_report,
        output_path=graph_confusion_matrix_figure_path,
    )

    baseline_metrics_path = resolve_project_path(baseline_metrics_output_path)

    if baseline_metrics_path.exists():
        logger.info("Baseline metrics found. Creating comparison report.")

        baseline_report = load_metrics_report(baseline_metrics_output_path)
        comparison_report = compare_model_reports(
            baseline_report=baseline_report,
            graph_report=metrics_report,
        )

        save_comparison_report(
            comparison_report=comparison_report,
            output_path=comparison_output_path,
        )
    else:
        logger.warning(
            "Baseline metrics not found at %s. "
            "Run `python scripts/train_baseline.py` to generate comparison report.",
            baseline_metrics_path,
        )

    logger.info("Graph-enhanced model training completed successfully.")


if __name__ == "__main__":
    main()