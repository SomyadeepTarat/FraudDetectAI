import networkx as nx
import pandas as pd
import pytest

from fraudgraph.features.graph_features import (
    build_node_feature_lookup,
    create_graph_feature_summary,
    create_graph_features_for_transactions,
    get_edge_features,
    get_node_degree_features,
    get_node_money_flow_features,
    prefix_feature_names,
    safe_divide,
)


def create_sample_graph() -> nx.DiGraph:
    graph = nx.DiGraph()

    graph.add_edge(
        "C1",
        "C4",
        transaction_count=2,
        total_amount=1200.0,
        average_amount=600.0,
    )
    graph.add_edge(
        "C2",
        "C4",
        transaction_count=1,
        total_amount=300.0,
        average_amount=300.0,
    )
    graph.add_edge(
        "C4",
        "M1",
        transaction_count=1,
        total_amount=100.0,
        average_amount=100.0,
    )

    return graph


def create_sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "step": [1, 2, 3],
            "type": ["TRANSFER", "TRANSFER", "CASH_OUT"],
            "amount": [500.0, 300.0, 100.0],
            "nameOrig": ["C1", "C2", "C4"],
            "nameDest": ["C4", "C4", "M1"],
            "oldbalanceOrg": [500.0, 300.0, 100.0],
            "newbalanceOrig": [0.0, 0.0, 0.0],
            "oldbalanceDest": [0.0, 0.0, 0.0],
            "newbalanceDest": [500.0, 300.0, 100.0],
            "isFraud": [1, 0, 0],
            "isFlaggedFraud": [0, 0, 0],
        }
    )


def test_safe_divide_returns_zero_for_zero_denominator() -> None:
    assert safe_divide(10.0, 0.0) == 0.0


def test_safe_divide_returns_expected_value() -> None:
    assert safe_divide(10.0, 2.0) == pytest.approx(5.0)


def test_get_node_degree_features_for_existing_node() -> None:
    graph = create_sample_graph()

    features = get_node_degree_features(graph, "C4")

    assert features["in_degree"] == pytest.approx(2.0)
    assert features["out_degree"] == pytest.approx(1.0)
    assert features["total_degree"] == pytest.approx(3.0)


def test_get_node_degree_features_for_missing_node_returns_zeroes() -> None:
    graph = create_sample_graph()

    features = get_node_degree_features(graph, "UNKNOWN")

    assert features == {
        "in_degree": 0.0,
        "out_degree": 0.0,
        "total_degree": 0.0,
    }


def test_get_node_money_flow_features_for_existing_node() -> None:
    graph = create_sample_graph()

    features = get_node_money_flow_features(graph, "C4")

    assert features["total_received_amount"] == pytest.approx(1500.0)
    assert features["total_sent_amount"] == pytest.approx(100.0)
    assert features["incoming_transaction_count"] == pytest.approx(3.0)
    assert features["outgoing_transaction_count"] == pytest.approx(1.0)
    assert features["avg_received_amount"] == pytest.approx(500.0)
    assert features["avg_sent_amount"] == pytest.approx(100.0)

def test_get_edge_features_for_existing_edge() -> None:
    graph = create_sample_graph()

    features = get_edge_features(graph, "C1", "C4")

    assert features["edge_transaction_count"] == pytest.approx(2.0)
    assert features["edge_total_amount"] == pytest.approx(1200.0)
    assert features["edge_avg_amount"] == pytest.approx(600.0)

    assert "edge_fraud_count" not in features
    assert "edge_fraud_rate" not in features

def test_get_edge_features_for_missing_edge_returns_zeroes() -> None:
    graph = create_sample_graph()

    features = get_edge_features(graph, "M1", "C1")

    assert features == {
        "edge_transaction_count": 0.0,
        "edge_total_amount": 0.0,
        "edge_avg_amount": 0.0,
    }

def test_build_node_feature_lookup_contains_all_nodes() -> None:
    graph = create_sample_graph()

    lookup = build_node_feature_lookup(graph)

    assert set(lookup.keys()) == {"C1", "C2", "C4", "M1"}
    assert lookup["C4"]["in_degree"] == pytest.approx(2.0)
    assert "incoming_fraud_rate" not in lookup["C4"]
    assert "outgoing_fraud_rate" not in lookup["C4"]


def test_prefix_feature_names_adds_prefix() -> None:
    features = {"in_degree": 2.0, "out_degree": 1.0}

    prefixed = prefix_feature_names(features, "sender")

    assert prefixed == {
        "sender_in_degree": 2.0,
        "sender_out_degree": 1.0,
    }


def test_create_graph_features_for_transactions_adds_expected_columns() -> None:
    graph = create_sample_graph()
    dataframe = create_sample_dataframe()

    enhanced_dataframe = create_graph_features_for_transactions(
        dataframe=dataframe,
        graph=graph,
        source_column="nameOrig",
        destination_column="nameDest",
    )

    expected_columns = {
        "sender_in_degree",
        "sender_out_degree",
        "receiver_in_degree",
        "receiver_out_degree",
        "sender_total_sent_amount",
        "receiver_total_received_amount",
        "sender_receiver_edge_transaction_count",
        "sender_receiver_edge_total_amount",
    }

    forbidden_columns = {
        "sender_incoming_fraud_count",
        "sender_outgoing_fraud_count",
        "receiver_incoming_fraud_count",
        "receiver_outgoing_fraud_count",
        "sender_incoming_fraud_rate",
        "sender_outgoing_fraud_rate",
        "receiver_incoming_fraud_rate",
        "receiver_outgoing_fraud_rate",
        "sender_receiver_edge_fraud_count",
        "sender_receiver_edge_fraud_rate",
    }

    assert expected_columns.issubset(set(enhanced_dataframe.columns))
    assert forbidden_columns.isdisjoint(set(enhanced_dataframe.columns))
    assert len(enhanced_dataframe) == len(dataframe)


def test_create_graph_features_for_transactions_values_are_correct() -> None:
    graph = create_sample_graph()
    dataframe = create_sample_dataframe()

    enhanced_dataframe = create_graph_features_for_transactions(
        dataframe=dataframe,
        graph=graph,
        source_column="nameOrig",
        destination_column="nameDest",
    )

    first_row = enhanced_dataframe.iloc[0]

    assert first_row["nameOrig"] == "C1"
    assert first_row["nameDest"] == "C4"
    assert first_row["sender_out_degree"] == pytest.approx(1.0)
    assert first_row["sender_total_sent_amount"] == pytest.approx(1200.0)
    assert first_row["receiver_in_degree"] == pytest.approx(2.0)
    assert first_row["receiver_total_received_amount"] == pytest.approx(1500.0)
    assert first_row["sender_receiver_edge_transaction_count"] == pytest.approx(2.0)
    assert first_row["sender_receiver_edge_total_amount"] == pytest.approx(1200.0)

    assert "receiver_incoming_fraud_rate" not in enhanced_dataframe.columns
    assert "sender_receiver_edge_fraud_rate" not in enhanced_dataframe.columns


def test_create_graph_feature_summary_returns_expected_structure() -> None:
    graph = create_sample_graph()
    dataframe = create_sample_dataframe()

    enhanced_dataframe = create_graph_features_for_transactions(
        dataframe=dataframe,
        graph=graph,
        source_column="nameOrig",
        destination_column="nameDest",
    )

    summary = create_graph_feature_summary(
        dataframe=enhanced_dataframe,
        graph_feature_columns=[
            "sender_out_degree",
            "receiver_in_degree",
            "sender_receiver_edge_transaction_count",
        ],
        target_column="isFraud",
    )

    assert summary["dataset_shape"]["num_rows"] == 3
    assert summary["graph_feature_count"] == 3
    assert "sender_out_degree" in summary["graph_features"]
    assert "mean_by_class" in summary["graph_features"]["sender_out_degree"]