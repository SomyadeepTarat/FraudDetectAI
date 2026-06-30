import pandas as pd

from fraudgraph.graph.build_graph import (
    build_transaction_graph,
    sample_graph_dataframe,
    save_transaction_graph,
)
from fraudgraph.graph.graph_utils import (
    calculate_graph_summary,
    create_degree_artifacts,
    save_graph_summary,
)
from fraudgraph.utils.config import load_yaml_config
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def main() -> None:
    """

    Steps:
        1. Load config.
        2. Load cleaned transaction dataset.
        3. Optionally sample rows for graph construction.
        4. Build directed transaction graph.
        5. Save graph artifact.
        6. Calculate graph summary.
        7. Save graph summary and degree plots.
    """
    config = load_yaml_config("configs/config.yaml")

    cleaned_data_path = config["data"]["interim_data_path"]
    graph_config = config["graph"]

    source_column = graph_config["source_column"]
    destination_column = graph_config["destination_column"]
    amount_column = graph_config["amount_column"]
    transaction_type_column = graph_config["transaction_type_column"]
    target_column = graph_config["target_column"]
    step_column = graph_config["step_column"]

    max_graph_rows = int(graph_config["max_graph_rows"])
    random_seed = int(graph_config["random_seed"])

    graph_output_path = graph_config["graph_output_path"]
    graph_summary_output_path = graph_config["graph_summary_output_path"]

    top_k_nodes = int(graph_config["top_k_nodes"])
    top_receivers_plot_path = graph_config["top_receivers_plot_path"]
    top_senders_plot_path = graph_config["top_senders_plot_path"]

    resolved_cleaned_data_path = resolve_project_path(cleaned_data_path)

    if not resolved_cleaned_data_path.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found at {resolved_cleaned_data_path}. "
            "Run `python scripts/make_dataset.py` before building the graph."
        )

    logger.info("Loading cleaned dataset from: %s", resolved_cleaned_data_path)
    dataframe = pd.read_parquet(resolved_cleaned_data_path)
    logger.info("Loaded cleaned dataset with shape: %s", dataframe.shape)

    graph_dataframe = sample_graph_dataframe(
        dataframe=dataframe,
        max_rows=max_graph_rows,
        target_column=target_column,
        random_seed=random_seed,
    )

    graph = build_transaction_graph(
        dataframe=graph_dataframe,
        source_column=source_column,
        destination_column=destination_column,
        amount_column=amount_column,
        transaction_type_column=transaction_type_column,
        target_column=target_column,
        step_column=step_column,
    )

    save_transaction_graph(
        graph=graph,
        output_path=graph_output_path,
    )

    graph_summary = calculate_graph_summary(graph)

    degree_artifacts = create_degree_artifacts(
        graph=graph,
        top_k=top_k_nodes,
        top_receivers_plot_path=top_receivers_plot_path,
        top_senders_plot_path=top_senders_plot_path,
    )

    graph_report = {
        "graph_summary": graph_summary,
        "degree_artifacts": degree_artifacts,
    }

    save_graph_summary(
        summary=graph_report,
        output_path=graph_summary_output_path,
    )

    logger.info("Transaction graph construction completed successfully.")


if __name__ == "__main__":
    main()