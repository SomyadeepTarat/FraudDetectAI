from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from fraudgraph.models.evaluate import evaluate_binary_classifier
from fraudgraph.models.model_registry import save_model
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def build_preprocessor(
    numeric_features: list[str],
    categorical_features: list[str],
    scale_numeric: bool,
) -> ColumnTransformer:

    if scale_numeric:
        numeric_transformer: Any = StandardScaler()
    else:
        numeric_transformer = "passthrough"

    categorical_transformer = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=True,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, numeric_features),
            ("categorical", categorical_transformer, categorical_features),
        ],
        remainder="drop",
    )

    return preprocessor


def calculate_scale_pos_weight(y_train: pd.Series) -> float:

    positive_count = int((y_train == 1).sum())
    negative_count = int((y_train == 0).sum())

    if positive_count == 0:
        logger.warning(
            "No positive examples found in y_train. Falling back to scale_pos_weight=1."
        )
        return 1.0

    return negative_count / positive_count


def build_logistic_regression_pipeline(
    numeric_features: list[str],
    categorical_features: list[str],
    random_seed: int,
) -> Pipeline:

    preprocessor = build_preprocessor(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        scale_numeric=True,
    )

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        solver="liblinear",
        random_state=random_seed,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    return pipeline


def build_random_forest_pipeline(
    numeric_features: list[str],
    categorical_features: list[str],
    random_seed: int,
    n_estimators: int,
    max_depth: int | None,
    min_samples_leaf: int,
) -> Pipeline:

    preprocessor = build_preprocessor(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        scale_numeric=False,
    )

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        class_weight="balanced_subsample",
        random_state=random_seed,
        n_jobs=-1,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    return pipeline


def build_xgboost_pipeline(
    numeric_features: list[str],
    categorical_features: list[str],
    random_seed: int,
    scale_pos_weight: float,
    n_estimators: int,
    max_depth: int,
    learning_rate: float,
    subsample: float,
    colsample_bytree: float,
) -> Pipeline:

    preprocessor = build_preprocessor(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        scale_numeric=False,
    )

    model = XGBClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        scale_pos_weight=scale_pos_weight,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=random_seed,
        n_jobs=-1,
        tree_method="hist",
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    return pipeline


def train_and_evaluate_model(
    model_name: str,
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    model_output_path: str | Path,
) -> dict[str, Any]:

    logger.info("Training model: %s", model_name)

    pipeline.fit(X_train, y_train)

    logger.info("Evaluating model: %s", model_name)

    metrics = evaluate_binary_classifier(
        model=pipeline,
        X_test=X_test,
        y_test=y_test,
        threshold=0.5,
    )

    save_model(
        model=pipeline,
        output_path=model_output_path,
    )

    logger.info(
        "%s metrics | precision=%.4f recall=%.4f f1=%.4f average_precision=%.4f",
        model_name,
        metrics["precision"],
        metrics["recall"],
        metrics["f1"],
        metrics["average_precision"],
    )

    return metrics


def train_baseline_models(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    numeric_features: list[str],
    categorical_features: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:

    random_seed = int(config["modeling"]["random_seed"])
    baseline_model_dir = config["modeling"]["baseline_model_dir"]
    baseline_model_config = config["modeling"]["baseline_models"]

    resolved_model_dir = resolve_project_path(baseline_model_dir)
    resolved_model_dir.mkdir(parents=True, exist_ok=True)

    metrics_by_model: dict[str, Any] = {}

    if baseline_model_config["logistic_regression"]["enabled"]:
        output_filename = baseline_model_config["logistic_regression"][
            "output_filename"
        ]

        pipeline = build_logistic_regression_pipeline(
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            random_seed=random_seed,
        )

        metrics_by_model["logistic_regression"] = train_and_evaluate_model(
            model_name="logistic_regression",
            pipeline=pipeline,
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            model_output_path=resolved_model_dir / output_filename,
        )

    if baseline_model_config["random_forest"]["enabled"]:
        random_forest_config = baseline_model_config["random_forest"]
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
            model_name="random_forest",
            pipeline=pipeline,
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            model_output_path=resolved_model_dir / output_filename,
        )

    if baseline_model_config["xgboost"]["enabled"]:
        xgboost_config = baseline_model_config["xgboost"]
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
            model_name="xgboost",
            pipeline=pipeline,
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
            model_output_path=resolved_model_dir / output_filename,
        )

    return metrics_by_model