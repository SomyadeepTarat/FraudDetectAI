import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def calculate_graph_summary(graph: nx.DiGraph) -> dict[str, Any]:

    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()

    if num_nodes == 0:
        return {
            "num_nodes": 0,
            "num_edges": 0,
            "density": 0.0,
            "num_weakly_connected_components": 0,
            "largest_weakly_connected_component_size": 0,
            "average_in_degree": 0.0,
            "average_out_degree": 0.0,
            "total_transaction_count": 0,
            "total_transaction_amount": 0.0,
            "total_fraud_count": 0,
            "edge_fraud_rate": 0.0,
        }

    in_degrees = dict(graph.in_degree())
    out_degrees = dict(graph.out_degree())

    weak_components = list(nx.weakly_connected_components(graph))
    largest_component_size = (
        max(len(component) for component in weak_components)
        if weak_components
        else 0
    )

    total_transaction_count = 0
    total_transaction_amount = 0.0
    total_fraud_count = 0

    for _, _, edge_data in graph.edges(data=True):
        total_transaction_count += int(edge_data.get("transaction_count", 0))
        total_transaction_amount += float(edge_data.get("total_amount", 0.0))
        total_fraud_count += int(edge_data.get("fraud_count", 0))

    edge_fraud_rate = (
        total_fraud_count / total_transaction_count
        if total_transaction_count > 0
        else 0.0
    )

    summary = {
        "num_nodes": int(num_nodes),
        "num_edges": int(num_edges),
        "density": float(nx.density(graph)),
        "num_weakly_connected_components": int(len(weak_components)),
        "largest_weakly_connected_component_size": int(largest_component_size),
        "average_in_degree": float(sum(in_degrees.values()) / num_nodes),
        "average_out_degree": float(sum(out_degrees.values()) / num_nodes),
        "total_transaction_count": int(total_transaction_count),
        "total_transaction_amount": float(total_transaction_amount),
        "total_fraud_count": int(total_fraud_count),
        "edge_fraud_rate": float(edge_fraud_rate),
    }

    return summary


def save_graph_summary(
    summary: dict[str, Any],
    output_path: str | Path,
) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    logger.info("Saved graph summary to: %s", resolved_output_path)

    return resolved_output_path


def get_top_nodes_by_degree(
    graph: nx.DiGraph,
    degree_type: str,
    top_k: int,
) -> pd.DataFrame:

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")

    if degree_type == "in":
        degree_view = graph.in_degree()
        degree_column = "in_degree"
    elif degree_type == "out":
        degree_view = graph.out_degree()
        degree_column = "out_degree"
    elif degree_type == "total":
        degree_view = graph.degree()
        degree_column = "total_degree"
    else:
        raise ValueError("degree_type must be one of: 'in', 'out', 'total'.")

    rows = [
        {
            "node": str(node),
            degree_column: int(degree),
        }
        for node, degree in degree_view
    ]

    result = (
        pd.DataFrame(rows)
        .sort_values(by=degree_column, ascending=False)
        .head(top_k)
        .reset_index(drop=True)
    )

    return result


def save_top_nodes_plot(
    top_nodes_dataframe: pd.DataFrame,
    degree_column: str,
    title: str,
    output_path: str | Path,
) -> Path:

    if "node" not in top_nodes_dataframe.columns:
        raise ValueError("top_nodes_dataframe must contain a 'node' column.")

    if degree_column not in top_nodes_dataframe.columns:
        raise ValueError(
            f"top_nodes_dataframe must contain degree column: {degree_column}"
        )

    resolved_output_path = ensure_parent_dir(output_path)

    plot_dataframe = top_nodes_dataframe.sort_values(
        by=degree_column,
        ascending=True,
    )

    plt.figure(figsize=(10, 7))
    plt.barh(plot_dataframe["node"], plot_dataframe[degree_column])
    plt.title(title)
    plt.xlabel(degree_column.replace("_", " ").title())
    plt.ylabel("Account Node")
    plt.tight_layout()
    plt.savefig(resolved_output_path, dpi=150)
    plt.close()

    logger.info("Saved top nodes plot to: %s", resolved_output_path)

    return resolved_output_path


def create_degree_artifacts(
    graph: nx.DiGraph,
    top_k: int,
    top_receivers_plot_path: str | Path,
    top_senders_plot_path: str | Path,
) -> dict[str, Any]:

    top_receivers = get_top_nodes_by_degree(
        graph=graph,
        degree_type="in",
        top_k=top_k,
    )

    top_senders = get_top_nodes_by_degree(
        graph=graph,
        degree_type="out",
        top_k=top_k,
    )

    save_top_nodes_plot(
        top_nodes_dataframe=top_receivers,
        degree_column="in_degree",
        title=f"Top {top_k} Receivers by In-Degree",
        output_path=top_receivers_plot_path,
    )

    save_top_nodes_plot(
        top_nodes_dataframe=top_senders,
        degree_column="out_degree",
        title=f"Top {top_k} Senders by Out-Degree",
        output_path=top_senders_plot_path,
    )

    artifacts = {
        "top_receivers_by_in_degree": top_receivers.to_dict(orient="records"),
        "top_senders_by_out_degree": top_senders.to_dict(orient="records"),
    }

    return artifacts