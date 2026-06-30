from pathlib import Path
from typing import Any

import pandas as pd

from fraudgraph.models.train_baselines import (
    build_logistic_regression_pipeline,
    build_random_forest_pipeline,
    build_xgboost_pipeline,
    calculate_scale_pos_weight,
    train_and_evaluate_model,
)
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def train_graph_enhanced_models(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    numeric_features: list[str],
    categorical_features: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:

    random_seed = int(config["graph_modeling"]["random_seed"])
    graph_model_dir = config["graph_modeling"]["graph_model_dir"]
    graph_model_config = config["graph_modeling"]["graph_models"]

    resolved_model_dir = resolve_project_path(graph_model_dir)
    resolved_model_dir.mkdir(parents=True, exist_ok=True)

    metrics_by_model: dict[str, Any] = {}

    if graph_model_config["logistic_regression"]["enabled"]:
        output_filename = graph_model_config["logistic_regression"]["output_filename"]

        pipeline = build_logistic_regression_pipeline(
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            random_seed=random_seed,
        )

        metrics_by_model["logistic_regression"] = train_and_evaluate_model(
            model_name="graph_logistic_regression",
            pipeline=pipeline,
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            model_output_path=resolved_model_dir / output_filename,
        )

    if graph_model_config["random_forest"]["enabled"]:
        random_forest_config = graph_model_config["random_forest"]
        output_filename = random_forest_config["output_filename"]

        pipeline = build_random_forest_pipeline(
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            random_seed=random_seed,
            n_estimators=int(random_forest_config["n_estimators"]),
            max_depth=int(random_forest_config["max_depth"])
            if random_forest_config["max_depth"] is not None
            else None,
            min_samples_leaf=int(random_forest_config["min_samples_leaf"]),
        )

        metrics_by_model["random_forest"] = train_and_evaluate_model(
            model_name="graph_random_forest",
            pipeline=pipeline,
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            model_output_path=resolved_model_dir / output_filename,
        )

    if graph_model_config["xgboost"]["enabled"]:
        xgboost_config = graph_model_config["xgboost"]
        output_filename = xgboost_config["output_filename"]

        scale_pos_weight = calculate_scale_pos_weight(y_train)

        pipeline = build_xgboost_pipeline(
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            random_seed=random_seed,
            scale_pos_weight=scale_pos_weight,
            n_estimators=int(xgboost_config["n_estimators"]),
            max_depth=int(xgboost_config["max_depth"]),
            learning_rate=float(xgboost_config["learning_rate"]),
            subsample=float(xgboost_config["subsample"]),
            colsample_bytree=float(xgboost_config["colsample_bytree"]),
        )

        metrics_by_model["xgboost"] = train_and_evaluate_model(
            model_name="graph_xgboost",
            pipeline=pipeline,
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            model_output_path=resolved_model_dir / output_filename,
        )

    return metrics_by_model


def build_graph_model_feature_lists(
    transaction_numeric_features: list[str],
    graph_feature_columns: list[str],
    categorical_features: list[str],
) -> tuple[list[str], list[str]]:

    numeric_features = transaction_numeric_features + graph_feature_columns

    duplicate_numeric_features = sorted(
        {
            feature
            for feature in numeric_features
            if numeric_features.count(feature) > 1
        }
    )

    if duplicate_numeric_features:
        raise ValueError(
            f"Duplicate numeric features found: {duplicate_numeric_features}"
        )

    overlapping_features = sorted(set(numeric_features) & set(categorical_features))

    if overlapping_features:
        raise ValueError(
            f"Features cannot be both numeric and categorical: {overlapping_features}"
        )

    return numeric_features, categorical_features