import pandas as pd

from fraudgraph.explainability.explain_model import (
    create_transaction_explanations,
    extract_model_feature_importance,
    load_feature_metadata,
    save_feature_importance_plot,
    save_feature_importance_report,
    save_transaction_explanations,
)
from fraudgraph.models.model_registry import load_model
from fraudgraph.utils.config import load_yaml_config
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def main() -> None:

    config = load_yaml_config("configs/config.yaml")

    explainability_config = config["explainability"]

    model_path = explainability_config["model_path"]
    scored_transactions_path = explainability_config["scored_transactions_path"]
    feature_metadata_path = explainability_config["feature_metadata_path"]

    feature_importance_report_path = explainability_config[
        "feature_importance_report_path"
    ]
    feature_importance_plot_path = explainability_config[
        "feature_importance_plot_path"
    ]
    transaction_explanations_output_path = explainability_config[
        "transaction_explanations_output_path"
    ]

    top_n_features = int(explainability_config["top_n_features"])
    top_n_transactions = int(explainability_config["top_n_transactions"])
    explanation_rules = explainability_config["explanation_rules"]

    logger.info("Loading feature metadata from: %s", feature_metadata_path)
    load_feature_metadata(feature_metadata_path)

    logger.info("Loading model from: %s", model_path)
    model = load_model(model_path)

    logger.info("Extracting model feature importance.")
    importance_dataframe = extract_model_feature_importance(model)

    save_feature_importance_report(
        importance_dataframe=importance_dataframe,
        output_path=feature_importance_report_path,
        top_n_features=top_n_features,
    )

    save_feature_importance_plot(
        importance_dataframe=importance_dataframe,
        output_path=feature_importance_plot_path,
        top_n_features=top_n_features,
    )

    resolved_scored_transactions_path = resolve_project_path(scored_transactions_path)

    if not resolved_scored_transactions_path.exists():
        raise FileNotFoundError(
            f"Scored transactions not found at {resolved_scored_transactions_path}. "
            "Run `python scripts/tune_threshold.py` first."
        )

    logger.info("Loading scored transactions from: %s", resolved_scored_transactions_path)
    scored_dataframe = pd.read_parquet(resolved_scored_transactions_path)
    logger.info("Loaded scored transactions with shape: %s", scored_dataframe.shape)

    transaction_explanations = create_transaction_explanations(
        scored_dataframe=scored_dataframe,
        explanation_rules=explanation_rules,
        top_n_transactions=top_n_transactions,
    )

    save_transaction_explanations(
        explanations=transaction_explanations,
        output_path=transaction_explanations_output_path,
    )

    logger.info("Explainability pipeline completed successfully.")


if __name__ == "__main__":
    main()