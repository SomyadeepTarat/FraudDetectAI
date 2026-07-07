import pandas as pd
import streamlit as st

from dashboard_utils import file_exists, format_number, load_json_file


st.set_page_config(
    page_title="Graph Explorer | FraudGraph AI",
    layout="wide",
)

st.title("Graph Explorer")

graph_summary_path = "reports/metrics/graph_summary.json"
graph_feature_summary_path = "reports/metrics/graph_feature_summary.json"
top_receivers_plot_path = "reports/figures/top_receivers_by_in_degree.png"
top_senders_plot_path = "reports/figures/top_senders_by_out_degree.png"

if not file_exists(graph_summary_path):
    st.error("Graph summary not found. Run `python scripts/build_transaction_graph.py` first.")
    st.stop()

graph_report = load_json_file(graph_summary_path)
graph_summary = graph_report.get("graph_summary", {})

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Nodes", format_number(graph_summary.get("num_nodes")))

with col2:
    st.metric("Edges", format_number(graph_summary.get("num_edges")))

with col3:
    st.metric(
        "Total Transactions",
        format_number(graph_summary.get("total_transaction_count")),
    )

with col4:
    st.metric(
        "Total Fraud Count",
        format_number(graph_summary.get("total_fraud_count")),
    )

col5, col6, col7 = st.columns(3)

with col5:
    st.metric("Weak Components", format_number(graph_summary.get("num_weakly_connected_components")))

with col6:
    st.metric(
        "Largest Component Size",
        format_number(graph_summary.get("largest_weakly_connected_component_size")),
    )

with col7:
    st.metric("Graph Density", graph_summary.get("density", "N/A"))

st.divider()

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Top Receivers by In-Degree")
    if file_exists(top_receivers_plot_path):
        st.image(str(top_receivers_plot_path))
    else:
        st.warning("Top receivers plot not found.")

with right_col:
    st.subheader("Top Senders by Out-Degree")
    if file_exists(top_senders_plot_path):
        st.image(str(top_senders_plot_path))
    else:
        st.warning("Top senders plot not found.")

st.divider()

st.subheader("Top Degree Artifacts")

degree_artifacts = graph_report.get("degree_artifacts", {})

receiver_records = degree_artifacts.get("top_receivers_by_in_degree", [])
sender_records = degree_artifacts.get("top_senders_by_out_degree", [])

col_a, col_b = st.columns(2)

with col_a:
    if receiver_records:
        st.dataframe(pd.DataFrame(receiver_records), use_container_width=True)
    else:
        st.info("No top receiver records available.")

with col_b:
    if sender_records:
        st.dataframe(pd.DataFrame(sender_records), use_container_width=True)
    else:
        st.info("No top sender records available.")

st.divider()

st.subheader("Graph Feature Summary")

if file_exists(graph_feature_summary_path):
    graph_feature_summary = load_json_file(graph_feature_summary_path)
    graph_features = graph_feature_summary.get("graph_features", {})

    feature_rows = []

    for feature_name, values in graph_features.items():
        mean_by_class = values.get("mean_by_class", {})
        feature_rows.append(
            {
                "feature": feature_name,
                "mean": values.get("mean"),
                "median": values.get("median"),
                "min": values.get("min"),
                "max": values.get("max"),
                "mean_non_fraud": mean_by_class.get("0"),
                "mean_fraud": mean_by_class.get("1"),
            }
        )

    if feature_rows:
        feature_summary_dataframe = pd.DataFrame(feature_rows)
        st.dataframe(feature_summary_dataframe, use_container_width=True)
    else:
        st.info("No graph feature summary rows available.")
else:
    st.warning("Graph feature summary not found. Run `python scripts/create_graph_features.py` first.")