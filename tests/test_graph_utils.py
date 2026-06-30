import networkx as nx
import pytest

from fraudgraph.graph.graph_utils import (
    calculate_graph_summary,
    get_top_nodes_by_degree,
)


def create_sample_graph() -> nx.DiGraph:
    graph = nx.DiGraph()

    graph.add_edge(
        "C1",
        "C4",
        transaction_count=2,
        total_amount=1200.0,
        fraud_count=2,
    )
    graph.add_edge(
        "C2",
        "C4",
        transaction_count=1,
        total_amount=300.0,
        fraud_count=0,
    )
    graph.add_edge(
        "C3",
        "C4",
        transaction_count=1,
        total_amount=200.0,
        fraud_count=0,
    )
    graph.add_edge(
        "C1",
        "M1",
        transaction_count=1,
        total_amount=100.0,
        fraud_count=0,
    )

    return graph


def test_calculate_graph_summary_returns_expected_values() -> None:
    graph = create_sample_graph()

    summary = calculate_graph_summary(graph)

    assert summary["num_nodes"] == 5
    assert summary["num_edges"] == 4
    assert summary["total_transaction_count"] == 5
    assert summary["total_transaction_amount"] == pytest.approx(1800.0)
    assert summary["total_fraud_count"] == 2
    assert summary["edge_fraud_rate"] == pytest.approx(2 / 5)
    assert summary["average_in_degree"] == pytest.approx(4 / 5)
    assert summary["average_out_degree"] == pytest.approx(4 / 5)


def test_calculate_graph_summary_handles_empty_graph() -> None:
    graph = nx.DiGraph()

    summary = calculate_graph_summary(graph)

    assert summary["num_nodes"] == 0
    assert summary["num_edges"] == 0
    assert summary["density"] == 0.0


def test_get_top_nodes_by_in_degree() -> None:
    graph = create_sample_graph()

    result = get_top_nodes_by_degree(
        graph=graph,
        degree_type="in",
        top_k=2,
    )

    assert result.iloc[0]["node"] == "C4"
    assert result.iloc[0]["in_degree"] == 3


def test_get_top_nodes_by_out_degree() -> None:
    graph = create_sample_graph()

    result = get_top_nodes_by_degree(
        graph=graph,
        degree_type="out",
        top_k=2,
    )

    assert result.iloc[0]["node"] == "C1"
    assert result.iloc[0]["out_degree"] == 2


def test_get_top_nodes_by_degree_rejects_invalid_degree_type() -> None:
    graph = create_sample_graph()

    with pytest.raises(ValueError, match="degree_type must be one of"):
        get_top_nodes_by_degree(
            graph=graph,
            degree_type="invalid",
            top_k=2,
        )