import json
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0

    return float(numerator / denominator)


def get_node_degree_features(graph: nx.DiGraph, node_id: str) -> dict[str, float]:
    if not graph.has_node(node_id):
        return {
            "in_degree": 0.0,
            "out_degree": 0.0,
            "total_degree": 0.0,
        }

    in_degree = float(graph.in_degree(node_id))
    out_degree = float(graph.out_degree(node_id))
    total_degree = float(graph.degree(node_id))

    return {
        "in_degree": in_degree,
        "out_degree": out_degree,
        "total_degree": total_degree,
    }


def get_node_money_flow_features(graph: nx.DiGraph, node_id: str) -> dict[str, float]:
    if not graph.has_node(node_id):
        return {
            "total_sent_amount": 0.0,
            "total_received_amount": 0.0,
            "outgoing_transaction_count": 0.0,
            "incoming_transaction_count": 0.0,
            "avg_sent_amount": 0.0,
            "avg_received_amount": 0.0,
        }

    total_sent_amount = 0.0
    total_received_amount = 0.0
    outgoing_transaction_count = 0.0
    incoming_transaction_count = 0.0

    for _, _, edge_data in graph.out_edges(node_id, data=True):
        total_sent_amount += float(edge_data.get("total_amount", 0.0))
        outgoing_transaction_count += float(edge_data.get("transaction_count", 0.0))

    for _, _, edge_data in graph.in_edges(node_id, data=True):
        total_received_amount += float(edge_data.get("total_amount", 0.0))
        incoming_transaction_count += float(edge_data.get("transaction_count", 0.0))

    avg_sent_amount = safe_divide(total_sent_amount, outgoing_transaction_count)
    avg_received_amount = safe_divide(
        total_received_amount,
        incoming_transaction_count,
    )

    return {
        "total_sent_amount": total_sent_amount,
        "total_received_amount": total_received_amount,
        "outgoing_transaction_count": outgoing_transaction_count,
        "incoming_transaction_count": incoming_transaction_count,
        "avg_sent_amount": avg_sent_amount,
        "avg_received_amount": avg_received_amount,
    }


def get_edge_features(
    graph: nx.DiGraph,
    source_node: str,
    destination_node: str,
) -> dict[str, float]:
    if not graph.has_edge(source_node, destination_node):
        return {
            "edge_transaction_count": 0.0,
            "edge_total_amount": 0.0,
            "edge_avg_amount": 0.0,
        }

    edge_data = graph[source_node][destination_node]

    return {
        "edge_transaction_count": float(edge_data.get("transaction_count", 0.0)),
        "edge_total_amount": float(edge_data.get("total_amount", 0.0)),
        "edge_avg_amount": float(edge_data.get("average_amount", 0.0)),
    }


def build_node_feature_lookup(graph: nx.DiGraph) -> dict[str, dict[str, float]]:
    logger.info("Building node feature lookup for %s nodes.", graph.number_of_nodes())

    lookup: dict[str, dict[str, float]] = {}

    for node_id in graph.nodes:
        node_key = str(node_id)

        degree_features = get_node_degree_features(graph, node_key)
        money_flow_features = get_node_money_flow_features(graph, node_key)

        lookup[node_key] = {
            **degree_features,
            **money_flow_features,
        }

    logger.info("Finished node feature lookup.")

    return lookup


def prefix_feature_names(
    feature_dict: dict[str, float],
    prefix: str,
) -> dict[str, float]:
    return {
        f"{prefix}_{feature_name}": float(feature_value)
        for feature_name, feature_value in feature_dict.items()
    }


def create_graph_features_for_transactions(
    dataframe: pd.DataFrame,
    graph: nx.DiGraph,
    source_column: str,
    destination_column: str,
) -> pd.DataFrame:
    required_columns = {source_column, destination_column}
    missing_columns = sorted(required_columns - set(dataframe.columns))

    if missing_columns:
        raise ValueError(
            f"Missing required columns for graph feature creation: {missing_columns}"
        )

    logger.info("Creating graph features for %s transaction rows.", len(dataframe))

    node_lookup = build_node_feature_lookup(graph)

    graph_feature_rows: list[dict[str, float]] = []

    empty_node_features = {
        "in_degree": 0.0,
        "out_degree": 0.0,
        "total_degree": 0.0,
        "total_sent_amount": 0.0,
        "total_received_amount": 0.0,
        "outgoing_transaction_count": 0.0,
        "incoming_transaction_count": 0.0,
        "avg_sent_amount": 0.0,
        "avg_received_amount": 0.0,
    }

    for row in dataframe[[source_column, destination_column]].itertuples(
        index=False,
        name=None,
    ):
        source_node = str(row[0])
        destination_node = str(row[1])

        sender_features = node_lookup.get(source_node, empty_node_features)
        receiver_features = node_lookup.get(destination_node, empty_node_features)

        edge_features = get_edge_features(
            graph=graph,
            source_node=source_node,
            destination_node=destination_node,
        )

        feature_row = {
            **prefix_feature_names(sender_features, "sender"),
            **prefix_feature_names(receiver_features, "receiver"),
            "sender_receiver_edge_transaction_count": edge_features[
                "edge_transaction_count"
            ],
            "sender_receiver_edge_total_amount": edge_features["edge_total_amount"],
            "sender_receiver_edge_avg_amount": edge_features["edge_avg_amount"],
        }

        graph_feature_rows.append(feature_row)

    graph_features_dataframe = pd.DataFrame(graph_feature_rows)

    enhanced_dataframe = pd.concat(
        [
            dataframe.reset_index(drop=True),
            graph_features_dataframe.reset_index(drop=True),
        ],
        axis=1,
    )

    logger.info(
        "Created graph-enhanced dataset with shape: %s",
        enhanced_dataframe.shape,
    )

    return enhanced_dataframe


def create_graph_feature_summary(
    dataframe: pd.DataFrame,
    graph_feature_columns: list[str],
    target_column: str,
) -> dict[str, Any]:
    missing_columns = sorted(
        set(graph_feature_columns + [target_column]) - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"Missing columns for graph feature summary: {missing_columns}"
        )

    summary: dict[str, Any] = {
        "dataset_shape": {
            "num_rows": int(dataframe.shape[0]),
            "num_columns": int(dataframe.shape[1]),
        },
        "graph_feature_count": int(len(graph_feature_columns)),
        "graph_features": {},
    }

    for feature_column in graph_feature_columns:
        feature_series = dataframe[feature_column]

        summary["graph_features"][feature_column] = {
            "mean": float(feature_series.mean()),
            "median": float(feature_series.median()),
            "std": float(feature_series.std()) if len(feature_series) > 1 else 0.0,
            "min": float(feature_series.min()),
            "max": float(feature_series.max()),
            "mean_by_class": {
                str(class_value): float(class_series.mean())
                for class_value, class_series in dataframe.groupby(target_column)[
                    feature_column
                ]
            },
        }

    return summary


def save_graph_enhanced_dataset(
    dataframe: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    resolved_output_path = ensure_parent_dir(output_path)

    dataframe.to_parquet(resolved_output_path, index=False)

    logger.info("Saved graph-enhanced dataset to: %s", resolved_output_path)

    return resolved_output_path


def save_graph_feature_summary(
    summary: dict[str, Any],
    output_path: str | Path,
) -> Path:
    resolved_output_path = ensure_parent_dir(output_path)

    with resolved_output_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    logger.info("Saved graph feature summary to: %s", resolved_output_path)

    return resolved_output_path