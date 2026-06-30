import pytest

from fraudgraph.models.train_graph_enhanced import build_graph_model_feature_lists


def test_build_graph_model_feature_lists_combines_transaction_and_graph_features() -> None:
    transaction_numeric_features = ["amount", "origin_balance_delta"]
    graph_feature_columns = ["sender_out_degree", "receiver_in_degree"]
    categorical_features = ["type"]

    numeric_features, returned_categorical_features = build_graph_model_feature_lists(
        transaction_numeric_features=transaction_numeric_features,
        graph_feature_columns=graph_feature_columns,
        categorical_features=categorical_features,
    )

    assert numeric_features == [
        "amount",
        "origin_balance_delta",
        "sender_out_degree",
        "receiver_in_degree",
    ]
    assert returned_categorical_features == ["type"]


def test_build_graph_model_feature_lists_raises_for_duplicate_numeric_features() -> None:
    transaction_numeric_features = ["amount", "sender_out_degree"]
    graph_feature_columns = ["sender_out_degree", "receiver_in_degree"]
    categorical_features = ["type"]

    with pytest.raises(ValueError, match="Duplicate numeric features"):
        build_graph_model_feature_lists(
            transaction_numeric_features=transaction_numeric_features,
            graph_feature_columns=graph_feature_columns,
            categorical_features=categorical_features,
        )


def test_build_graph_model_feature_lists_raises_for_numeric_categorical_overlap() -> None:
    transaction_numeric_features = ["amount"]
    graph_feature_columns = ["sender_out_degree"]
    categorical_features = ["type", "amount"]

    with pytest.raises(ValueError, match="both numeric and categorical"):
        build_graph_model_feature_lists(
            transaction_numeric_features=transaction_numeric_features,
            graph_feature_columns=graph_feature_columns,
            categorical_features=categorical_features,
        )