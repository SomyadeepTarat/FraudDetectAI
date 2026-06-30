import networkx as nx
import pandas as pd
import pytest

from fraudgraph.graph.build_graph import (
    add_or_update_account_node,
    build_transaction_graph,
    sample_graph_dataframe,
    validate_graph_columns,
)


def create_sample_transaction_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "step": [1, 1, 2, 3, 4],
            "type": ["PAYMENT", "TRANSFER", "TRANSFER", "CASH_OUT", "TRANSFER"],
            "amount": [100.0, 500.0, 300.0, 200.0, 700.0],
            "nameOrig": ["C1", "C1", "C2", "C3", "C1"],
            "nameDest": ["M1", "C4", "C4", "C4", "C4"],
            "isFraud": [0, 1, 0, 0, 1],
        }
    )


def test_validate_graph_columns_passes_for_valid_dataframe() -> None:
    dataframe = create_sample_transaction_dataframe()

    validate_graph_columns(
        dataframe=dataframe,
        source_column="nameOrig",
        destination_column="nameDest",
        amount_column="amount",
        transaction_type_column="type",
        target_column="isFraud",
        step_column="step",
    )


def test_validate_graph_columns_raises_for_missing_column() -> None:
    dataframe = create_sample_transaction_dataframe().drop(columns=["nameDest"])

    with pytest.raises(ValueError, match="Missing required graph columns"):
        validate_graph_columns(
            dataframe=dataframe,
            source_column="nameOrig",
            destination_column="nameDest",
            amount_column="amount",
            transaction_type_column="type",
            target_column="isFraud",
            step_column="step",
        )


def test_sample_graph_dataframe_preserves_all_fraud_rows_when_possible() -> None:
    dataframe = create_sample_transaction_dataframe()

    sampled_dataframe = sample_graph_dataframe(
        dataframe=dataframe,
        max_rows=4,
        target_column="isFraud",
        random_seed=42,
    )

    assert len(sampled_dataframe) == 4
    assert int(sampled_dataframe["isFraud"].sum()) == 2


def test_add_or_update_account_node_adds_and_updates_roles() -> None:
    graph = nx.DiGraph()

    add_or_update_account_node(graph, "C1", "sender")
    add_or_update_account_node(graph, "C1", "receiver")

    assert graph.has_node("C1")
    assert graph.nodes["C1"]["roles"] == ["receiver", "sender"]


def test_build_transaction_graph_creates_expected_nodes_and_edges() -> None:
    dataframe = create_sample_transaction_dataframe()

    graph = build_transaction_graph(
        dataframe=dataframe,
        source_column="nameOrig",
        destination_column="nameDest",
        amount_column="amount",
        transaction_type_column="type",
        target_column="isFraud",
        step_column="step",
    )

    assert isinstance(graph, nx.DiGraph)
    assert graph.number_of_nodes() == 5
    assert graph.number_of_edges() == 4

    assert graph.has_edge("C1", "C4")
    edge_data = graph["C1"]["C4"]

    assert edge_data["transaction_count"] == 2
    assert edge_data["total_amount"] == pytest.approx(1200.0)
    assert edge_data["fraud_count"] == 2
    assert edge_data["fraud_rate"] == pytest.approx(1.0)
    assert edge_data["average_amount"] == pytest.approx(600.0)
    assert edge_data["transaction_types"] == ["TRANSFER"]
    assert edge_data["min_step"] == 1
    assert edge_data["max_step"] == 4