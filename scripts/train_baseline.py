import pandas as pd

from fraudgraph.features.transaction_features import (
    build_feature_target_matrices,
    create_train_test_split,
    save_feature_columns,
    stratified_sample_dataframe,
)
from fraudgraph.models.evaluate import plot_confusion_matrices, save_metrics_report
from fraudgraph.models.train_baselines import train_baseline_models
from fraudgraph.utils.config import load_yaml_config
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def main() -> None:
    """
    Steps:
        1. Load config.
        2. Load cleaned dataset.
        3. Optionally sample large dataset.
        4. Build X and y.
        5. Create stratified train/test split.
        6. Train baseline models.
        7. Save models, metrics, plots, and feature metadata.
    """
    config = load_yaml_config("configs/config.yaml")

    cleaned_data_path = config["data"]["interim_data_path"]
    target_column = config["target"]["name"]

    numeric_features = config["modeling"]["numeric_features"]
    categorical_features = config["modeling"]["categorical_features"]

    test_size = float(config["modeling"]["test_size"])
    random_seed = int(config["modeling"]["random_seed"])
    max_training_rows = int(config["modeling"]["max_training_rows"])

    metrics_output_path = config["modeling"]["metrics_output_path"]
    confusion_matrix_figure_path = config["modeling"]["confusion_matrix_figure_path"]
    feature_columns_output_path = config["modeling"]["feature_columns_output_path"]

    resolved_cleaned_data_path = resolve_project_path(cleaned_data_path)

    if not resolved_cleaned_data_path.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found at {resolved_cleaned_data_path}. "
            "Run `python scripts/make_dataset.py` first."
        )

    logger.info("Loading cleaned dataset from: %s", resolved_cleaned_data_path)
    dataframe = pd.read_parquet(resolved_cleaned_data_path)
    logger.info("Loaded dataset with shape: %s", dataframe.shape)

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

    logger.info("Feature matrix shape: %s", X.shape)
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
        output_path=feature_columns_output_path,
    )

    metrics_by_model = train_baseline_models(
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
            "source_path": str(resolved_cleaned_data_path),
            "num_rows_used": int(len(sampled_dataframe)),
            "num_features": int(X.shape[1]),
            "test_size": test_size,
            "target_distribution": {
                str(label): int(count)
                for label, count in y.value_counts().to_dict().items()
            },
        },
        "features": {
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
        },
        "models": metrics_by_model,
    }

    save_metrics_report(
        metrics_report=metrics_report,
        output_path=metrics_output_path,
    )

    plot_confusion_matrices(
        metrics_report=metrics_report,
        output_path=confusion_matrix_figure_path,
    )

    logger.info("Baseline model training completed successfully.")


if __name__ == "__main__":
    main()