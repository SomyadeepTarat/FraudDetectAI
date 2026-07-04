import pandas as pd

from fraudgraph.features.transaction_features import (
    build_feature_target_matrices,
    create_train_test_split,
    stratified_sample_dataframe,
)
from fraudgraph.models.evaluate import get_positive_class_scores
from fraudgraph.models.model_registry import load_model
from fraudgraph.models.risk_scoring import (
    create_risk_scoring_report,
    save_risk_scoring_report,
    save_scored_transactions,
    score_transactions,
)
from fraudgraph.models.threshold_tuning import (
    create_threshold_tuning_report,
    evaluate_thresholds,
    generate_thresholds,
    save_threshold_curve_plot,
    save_threshold_tuning_report,
    select_best_threshold,
)
from fraudgraph.models.train_graph_enhanced import build_graph_model_feature_lists
from fraudgraph.utils.config import load_yaml_config
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def main() -> None:

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

    feature_columns = numeric_features + categorical_features

    graph_modeling_config = config["graph_modeling"]
    threshold_config = config["threshold_tuning"]

    test_size = float(graph_modeling_config["test_size"])
    random_seed = int(graph_modeling_config["random_seed"])
    max_training_rows = int(graph_modeling_config["max_training_rows"])

    model_name = threshold_config["model_name"]
    model_path = threshold_config["model_path"]

    threshold_min = float(threshold_config["threshold_min"])
    threshold_max = float(threshold_config["threshold_max"])
    threshold_step = float(threshold_config["threshold_step"])
    optimization_metric = threshold_config["optimization_metric"]
    minimum_recall = float(threshold_config["minimum_recall"])

    threshold_results_output_path = threshold_config["threshold_results_output_path"]
    threshold_curve_output_path = threshold_config["threshold_curve_output_path"]
    risk_scoring_report_output_path = threshold_config[
        "risk_scoring_report_output_path"
    ]
    scored_transactions_output_path = threshold_config[
        "scored_transactions_output_path"
    ]
    risk_band_config = threshold_config["risk_bands"]

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

    X_train, X_test, y_train, y_test = create_train_test_split(
        X=X,
        y=y,
        test_size=test_size,
        random_seed=random_seed,
    )

    logger.info("Loading trained model from: %s", model_path)
    model = load_model(model_path)

    y_scores = get_positive_class_scores(
        model=model,
        X=X_test,
    )

    thresholds = generate_thresholds(
        threshold_min=threshold_min,
        threshold_max=threshold_max,
        threshold_step=threshold_step,
    )

    threshold_results = evaluate_thresholds(
        y_true=y_test,
        y_scores=y_scores,
        thresholds=thresholds,
    )

    best_threshold_result = select_best_threshold(
        threshold_results=threshold_results,
        optimization_metric=optimization_metric,
        minimum_recall=minimum_recall,
    )

    best_threshold = float(best_threshold_result["threshold"])

    logger.info(
        "Best threshold selected: %.4f | precision=%.4f recall=%.4f f1=%.4f",
        best_threshold,
        best_threshold_result["precision"],
        best_threshold_result["recall"],
        best_threshold_result["f1"],
    )

    threshold_report = create_threshold_tuning_report(
        threshold_results=threshold_results,
        best_threshold_result=best_threshold_result,
        optimization_metric=optimization_metric,
        minimum_recall=minimum_recall,
        model_name=model_name,
    )

    save_threshold_tuning_report(
        report=threshold_report,
        output_path=threshold_results_output_path,
    )

    save_threshold_curve_plot(
        threshold_results=threshold_results,
        output_path=threshold_curve_output_path,
    )

    scored_dataframe = score_transactions(
        model=model,
        dataframe=sampled_dataframe,
        feature_columns=feature_columns,
        decision_threshold=best_threshold,
        risk_band_config=risk_band_config,
    )

    save_scored_transactions(
        scored_dataframe=scored_dataframe,
        output_path=scored_transactions_output_path,
    )

    risk_scoring_report = create_risk_scoring_report(
        scored_dataframe=scored_dataframe,
        target_column=target_column,
        decision_threshold=best_threshold,
    )

    save_risk_scoring_report(
        report=risk_scoring_report,
        output_path=risk_scoring_report_output_path,
    )

    logger.info("Threshold tuning and risk scoring completed successfully.")


if __name__ == "__main__":
    main()