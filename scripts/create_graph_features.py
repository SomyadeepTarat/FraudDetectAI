import pandas as pd

from fraudgraph.features.graph_features import (
    create_graph_feature_summary,
    create_graph_features_for_transactions,
    save_graph_enhanced_dataset,
    save_graph_feature_summary,
)
from fraudgraph.graph.build_graph import load_transaction_graph
from fraudgraph.utils.config import load_yaml_config
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def main() -> None:
    """
    Create graph-enhanced fraud dataset.

    Steps:
    load cleaned PaySim data
    load saved transaction graph
    calculate sender graph features
    calculate receiver graph features
    calculate edge graph features
    merge graph features with transaction rows
    save graph-enhanced parquet dataset
    save graph feature summary JSON
    
    """
    config = load_yaml_config("configs/config.yaml")

    cleaned_data_path = config["data"]["interim_data_path"]

    graph_config = config["graph"]
    graph_feature_config = config["graph_features"]

    graph_path = graph_config["graph_output_path"]
    source_column = graph_config["source_column"]
    destination_column = graph_config["destination_column"]
    target_column = graph_config["target_column"]

    graph_enhanced_dataset_path = graph_feature_config[
        "graph_enhanced_dataset_path"
    ]
    graph_feature_summary_path = graph_feature_config[
        "graph_feature_summary_path"
    ]
    graph_feature_columns = graph_feature_config["graph_feature_columns"]

    resolved_cleaned_data_path = resolve_project_path(cleaned_data_path)

    if not resolved_cleaned_data_path.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found at {resolved_cleaned_data_path}. "
            "Run `python scripts/make_dataset.py` first."
        )

    logger.info("Loading cleaned dataset from: %s", resolved_cleaned_data_path)
    dataframe = pd.read_parquet(resolved_cleaned_data_path)
    logger.info("Loaded cleaned dataset with shape: %s", dataframe.shape)

    graph = load_transaction_graph(graph_path)

    graph_enhanced_dataframe = create_graph_features_for_transactions(
        dataframe=dataframe,
        graph=graph,
        source_column=source_column,
        destination_column=destination_column,
    )

    save_graph_enhanced_dataset(
        dataframe=graph_enhanced_dataframe,
        output_path=graph_enhanced_dataset_path,
    )

    graph_feature_summary = create_graph_feature_summary(
        dataframe=graph_enhanced_dataframe,
        graph_feature_columns=graph_feature_columns,
        target_column=target_column,
    )

    save_graph_feature_summary(
        summary=graph_feature_summary,
        output_path=graph_feature_summary_path,
    )

    logger.info("Graph feature creation completed successfully.")


if __name__ == "__main__":
    main()