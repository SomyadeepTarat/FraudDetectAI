from pathlib import Path
import pickle

import networkx as nx
import pandas as pd

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def validate_graph_columns(
    dataframe: pd.DataFrame,
    source_column: str,
    destination_column: str,
    amount_column: str,
    transaction_type_column: str,
    target_column: str,
    step_column: str,
) -> None:

    required_columns = {
        source_column,
        destination_column,
        amount_column,
        transaction_type_column,
        target_column,
        step_column,
    }

    missing_columns = sorted(required_columns - set(dataframe.columns))

    if missing_columns:
        raise ValueError(f"Missing required graph columns: {missing_columns}")


def sample_graph_dataframe(
    dataframe: pd.DataFrame,
    max_rows: int | None,
    target_column: str,
    random_seed: int,
) -> pd.DataFrame:

    if max_rows is None or max_rows <= 0 or len(dataframe) <= max_rows:
        return dataframe.copy()

    if target_column not in dataframe.columns:
        raise ValueError(f"Target column not found: {target_column}")

    fraud_dataframe = dataframe[dataframe[target_column] == 1].copy()
    non_fraud_dataframe = dataframe[dataframe[target_column] == 0].copy()

    if len(fraud_dataframe) >= max_rows:
        sampled_dataframe = fraud_dataframe.sample(
            n=max_rows,
            random_state=random_seed,
        )
        return sampled_dataframe.reset_index(drop=True)

    remaining_rows = max_rows - len(fraud_dataframe)
    sampled_non_fraud_dataframe = non_fraud_dataframe.sample(
        n=min(remaining_rows, len(non_fraud_dataframe)),
        random_state=random_seed,
    )

    sampled_dataframe = pd.concat(
        [fraud_dataframe, sampled_non_fraud_dataframe],
        axis=0,
    )

    sampled_dataframe = sampled_dataframe.sample(
        frac=1.0,
        random_state=random_seed,
    ).reset_index(drop=True)

    logger.info(
        "Sampled graph dataframe from %s rows to %s rows while preserving %s fraud rows.",
        len(dataframe),
        len(sampled_dataframe),
        len(fraud_dataframe),
    )

    return sampled_dataframe


def add_or_update_account_node(
    graph: nx.DiGraph,
    account_id: str,
    role: str,
) -> None:

    if graph.has_node(account_id):
        existing_roles = set(graph.nodes[account_id].get("roles", []))
        existing_roles.add(role)
        graph.nodes[account_id]["roles"] = sorted(existing_roles)
    else:
        graph.add_node(account_id, roles=[role])


def build_transaction_graph(
    dataframe: pd.DataFrame,
    source_column: str,
    destination_column: str,
    amount_column: str,
    transaction_type_column: str,
    target_column: str,
    step_column: str,
) -> nx.DiGraph:

    validate_graph_columns(
        dataframe=dataframe,
        source_column=source_column,
        destination_column=destination_column,
        amount_column=amount_column,
        transaction_type_column=transaction_type_column,
        target_column=target_column,
        step_column=step_column,
    )

    graph = nx.DiGraph()

    logger.info("Building transaction graph from %s rows.", len(dataframe))

    for row in dataframe[
        [
            source_column,
            destination_column,
            amount_column,
            transaction_type_column,
            target_column,
            step_column,
        ]
    ].itertuples(index=False, name=None):
        source_account = str(row[0])
        destination_account = str(row[1])
        amount = float(row[2])
        transaction_type = str(row[3])
        is_fraud = int(row[4])
        step = int(row[5])

        add_or_update_account_node(
            graph=graph,
            account_id=source_account,
            role="sender",
        )
        add_or_update_account_node(
            graph=graph,
            account_id=destination_account,
            role="receiver",
        )

        if graph.has_edge(source_account, destination_account):
            edge_data = graph[source_account][destination_account]
            edge_data["transaction_count"] += 1
            edge_data["total_amount"] += amount
            edge_data["fraud_count"] += is_fraud
            edge_data["transaction_types"].add(transaction_type)
            edge_data["min_step"] = min(edge_data["min_step"], step)
            edge_data["max_step"] = max(edge_data["max_step"], step)
        else:
            graph.add_edge(
                source_account,
                destination_account,
                transaction_count=1,
                total_amount=amount,
                fraud_count=is_fraud,
                transaction_types={transaction_type},
                min_step=step,
                max_step=step,
            )

    for source_account, destination_account, edge_data in graph.edges(data=True):
        edge_data["transaction_types"] = sorted(edge_data["transaction_types"])
        edge_data["average_amount"] = (
            edge_data["total_amount"] / edge_data["transaction_count"]
        )
        edge_data["fraud_rate"] = (
            edge_data["fraud_count"] / edge_data["transaction_count"]
        )

    logger.info(
        "Built graph with %s nodes and %s edges.",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )

    return graph


import pickle
from pathlib import Path

import networkx as nx

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def save_transaction_graph(
    graph: nx.DiGraph,
    output_path: str | Path,
) -> Path:
    resolved_output_path = ensure_parent_dir(output_path)

    with open(resolved_output_path, "wb") as file:
        pickle.dump(graph, file)

    logger.info("Saved transaction graph to: %s", resolved_output_path)

    return resolved_output_path


def load_transaction_graph(graph_path: str | Path) -> nx.DiGraph:
    from fraudgraph.utils.paths import resolve_project_path

    resolved_graph_path = resolve_project_path(graph_path)

    if not resolved_graph_path.exists():
        raise FileNotFoundError(f"Graph artifact not found: {resolved_graph_path}")

    with open(resolved_graph_path, "rb") as file:
        graph = pickle.load(file)

    logger.info(
        "Loaded graph from %s with %s nodes and %s edges.",
        resolved_graph_path,
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )

    return graph