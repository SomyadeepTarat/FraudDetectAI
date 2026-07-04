import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir, resolve_project_path

logger = get_logger(__name__)


def load_feature_metadata(feature_metadata_path: str | Path) -> dict[str, Any]:

    resolved_path = resolve_project_path(feature_metadata_path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Feature metadata file not found: {resolved_path}")

    with resolved_path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    required_keys = {"numeric_features", "categorical_features", "all_features"}
    missing_keys = required_keys - set(metadata.keys())

    if missing_keys:
        raise ValueError(f"Feature metadata missing required keys: {missing_keys}")

    return metadata


def get_fitted_pipeline_components(model: Pipeline) -> tuple[Any, Any]:

    if not isinstance(model, Pipeline):
        raise ValueError("Model must be a sklearn Pipeline.")

    if "preprocessor" not in model.named_steps:
        raise ValueError("Pipeline does not contain a 'preprocessor' step.")

    if "model" not in model.named_steps:
        raise ValueError("Pipeline does not contain a 'model' step.")

    return model.named_steps["preprocessor"], model.named_steps["model"]


def get_transformed_feature_names(
    model: Pipeline,
) -> list[str]:

    preprocessor, _ = get_fitted_pipeline_components(model)

    if not hasattr(preprocessor, "get_feature_names_out"):
        raise ValueError("Preprocessor does not support get_feature_names_out().")

    raw_feature_names = preprocessor.get_feature_names_out()

    cleaned_feature_names = []

    for feature_name in raw_feature_names:
        cleaned_name = str(feature_name)

        if cleaned_name.startswith("numeric__"):
            cleaned_name = cleaned_name.replace("numeric__", "", 1)

        if cleaned_name.startswith("categorical__"):
            cleaned_name = cleaned_name.replace("categorical__", "", 1)

        cleaned_feature_names.append(cleaned_name)

    return cleaned_feature_names


def extract_model_feature_importance(
    model: Pipeline,
) -> pd.DataFrame:

    _, estimator = get_fitted_pipeline_components(model)
    feature_names = get_transformed_feature_names(model)

    if hasattr(estimator, "feature_importances_"):
        importance_values = np.asarray(estimator.feature_importances_, dtype=float)

    elif hasattr(estimator, "coef_"):
        coefficients = np.asarray(estimator.coef_, dtype=float)

        if coefficients.ndim == 2:
            importance_values = np.abs(coefficients[0])
        else:
            importance_values = np.abs(coefficients)

    else:
        raise ValueError(
            "Estimator does not expose feature_importances_ or coef_. "
            "Cannot extract feature importance."
        )

    if len(feature_names) != len(importance_values):
        raise ValueError(
            "Feature name count does not match importance value count. "
            f"Got {len(feature_names)} feature names and {len(importance_values)} importances."
        )

    importance_dataframe = pd.DataFrame(
        {
            "feature_name": feature_names,
            "importance": importance_values,
        }
    )

    importance_dataframe = importance_dataframe.sort_values(
        by="importance",
        ascending=False,
    ).reset_index(drop=True)

    total_importance = float(importance_dataframe["importance"].sum())

    if total_importance > 0:
        importance_dataframe["importance_normalized"] = (
            importance_dataframe["importance"] / total_importance
        )
    else:
        importance_dataframe["importance_normalized"] = 0.0

    return importance_dataframe


def save_feature_importance_report(
    importance_dataframe: pd.DataFrame,
    output_path: str | Path,
    top_n_features: int,
) -> Path:
    
    if top_n_features <= 0:
        raise ValueError("top_n_features must be greater than 0.")

    resolved_output_path = ensure_parent_dir(output_path)

    top_features = importance_dataframe.head(top_n_features)

    payload = {
        "top_n_features": int(top_n_features),
        "features": top_features.to_dict(orient="records"),
    }

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    logger.info("Saved feature importance report to: %s", resolved_output_path)

    return resolved_output_path


def save_feature_importance_plot(
    importance_dataframe: pd.DataFrame,
    output_path: str | Path,
    top_n_features: int,
) -> Path:

    if top_n_features <= 0:
        raise ValueError("top_n_features must be greater than 0.")

    resolved_output_path = ensure_parent_dir(output_path)

    plot_dataframe = importance_dataframe.head(top_n_features).copy()
    plot_dataframe = plot_dataframe.sort_values(by="importance", ascending=True)

    plt.figure(figsize=(11, 8))
    plt.barh(plot_dataframe["feature_name"], plot_dataframe["importance"])
    plt.title(f"Top {top_n_features} Model Feature Importances")
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    plt.savefig(resolved_output_path, dpi=150)
    plt.close()

    logger.info("Saved feature importance plot to: %s", resolved_output_path)

    return resolved_output_path


def get_numeric_value(
    row: pd.Series,
    column_name: str,
    default: float = 0.0,
) -> float:

    if column_name not in row.index:
        return default

    value = row[column_name]

    if pd.isna(value):
        return default

    return float(value)


def get_string_value(
    row: pd.Series,
    column_name: str,
    default: str = "UNKNOWN",
) -> str:

    if column_name not in row.index:
        return default

    value = row[column_name]

    if pd.isna(value):
        return default

    return str(value)


def explain_transaction_with_rules(
    row: pd.Series,
    explanation_rules: dict[str, float],
) -> list[str]:

    reasons: list[str] = []

    fraud_probability = get_numeric_value(row, "fraud_probability")
    amount = get_numeric_value(row, "amount")
    transaction_type = get_string_value(row, "type")

    amount_to_balance_ratio = get_numeric_value(
        row,
        "amount_to_old_origin_balance_ratio",
    )
    is_origin_balance_emptied = get_numeric_value(
        row,
        "is_origin_balance_emptied",
    )
    receiver_incoming_fraud_rate = get_numeric_value(
        row,
        "receiver_incoming_fraud_rate",
    )
    sender_outgoing_fraud_rate = get_numeric_value(
        row,
        "sender_outgoing_fraud_rate",
    )
    edge_fraud_rate = get_numeric_value(
        row,
        "sender_receiver_edge_fraud_rate",
    )
    receiver_in_degree = get_numeric_value(
        row,
        "receiver_in_degree",
    )
    sender_out_degree = get_numeric_value(
        row,
        "sender_out_degree",
    )

    if fraud_probability >= explanation_rules["high_probability_threshold"]:
        reasons.append(
            f"Model assigned a high fraud probability of {fraud_probability:.3f}."
        )

    if transaction_type in {"TRANSFER", "CASH_OUT"}:
        reasons.append(
            f"Transaction type is {transaction_type}, which is commonly important in fraud patterns."
        )

    if amount_to_balance_ratio >= explanation_rules["high_amount_ratio_threshold"]:
        reasons.append(
            "Transaction amount is high relative to the sender's old balance."
        )

    if is_origin_balance_emptied == 1:
        reasons.append(
            "Sender's balance was emptied after the transaction."
        )

    if receiver_incoming_fraud_rate >= explanation_rules[
        "high_receiver_fraud_rate_threshold"
    ]:
        reasons.append(
            f"Receiver has a high incoming fraud rate of {receiver_incoming_fraud_rate:.3f}."
        )

    if sender_outgoing_fraud_rate >= explanation_rules[
        "high_sender_fraud_rate_threshold"
    ]:
        reasons.append(
            f"Sender has a high outgoing fraud rate of {sender_outgoing_fraud_rate:.3f}."
        )

    if edge_fraud_rate >= explanation_rules["high_edge_fraud_rate_threshold"]:
        reasons.append(
            f"This sender-receiver relationship has an edge fraud rate of {edge_fraud_rate:.3f}."
        )

    if receiver_in_degree >= explanation_rules["high_receiver_in_degree_threshold"]:
        reasons.append(
            f"Receiver has high in-degree with {receiver_in_degree:.0f} unique incoming senders."
        )

    if sender_out_degree >= explanation_rules["high_sender_out_degree_threshold"]:
        reasons.append(
            f"Sender has high out-degree with {sender_out_degree:.0f} unique outgoing receivers."
        )

    if amount > 0 and not reasons:
        reasons.append(
            "Transaction received a non-zero risk score, but no rule threshold was strongly triggered."
        )

    return reasons


def create_transaction_explanations(
    scored_dataframe: pd.DataFrame,
    explanation_rules: dict[str, float],
    top_n_transactions: int,
) -> list[dict[str, Any]]:

    if top_n_transactions <= 0:
        raise ValueError("top_n_transactions must be greater than 0.")

    required_columns = {
        "fraud_probability",
        "predicted_fraud",
        "risk_band",
        "nameOrig",
        "nameDest",
        "amount",
        "type",
    }

    missing_columns = sorted(required_columns - set(scored_dataframe.columns))

    if missing_columns:
        raise ValueError(
            f"Missing required columns for transaction explanations: {missing_columns}"
        )

    top_transactions = scored_dataframe.sort_values(
        by="fraud_probability",
        ascending=False,
    ).head(top_n_transactions)

    explanations: list[dict[str, Any]] = []

    for index, row in top_transactions.iterrows():
        reasons = explain_transaction_with_rules(
            row=row,
            explanation_rules=explanation_rules,
        )

        explanation = {
            "rank": int(len(explanations) + 1),
            "row_index": int(index) if isinstance(index, (int, np.integer)) else str(index),
            "sender": get_string_value(row, "nameOrig"),
            "receiver": get_string_value(row, "nameDest"),
            "transaction_type": get_string_value(row, "type"),
            "amount": get_numeric_value(row, "amount"),
            "fraud_probability": get_numeric_value(row, "fraud_probability"),
            "predicted_fraud": int(get_numeric_value(row, "predicted_fraud")),
            "risk_band": get_string_value(row, "risk_band"),
            "actual_is_fraud": int(get_numeric_value(row, "isFraud")),
            "reasons": reasons,
        }

        explanations.append(explanation)

    return explanations


def save_transaction_explanations(
    explanations: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    payload = {
        "num_explanations": int(len(explanations)),
        "explanations": explanations,
    }

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    logger.info("Saved transaction explanations to: %s", resolved_output_path)

    return resolved_output_path