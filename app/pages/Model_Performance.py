import pandas as pd
import streamlit as st

from dashboard_utils import (
    extract_comparison_table,
    extract_model_metric_table,
    file_exists,
    load_json_file,
)


st.set_page_config(
    page_title="Model Performance | FraudGraph AI",
    page_icon="📈",
    layout="wide",
)

st.title("Model Performance")

baseline_metrics_path = "reports/metrics/baseline_model_metrics.json"
graph_metrics_path = "reports/metrics/graph_model_metrics.json"
comparison_path = "reports/metrics/baseline_vs_graph_comparison.json"
baseline_cm_path = "reports/figures/baseline_confusion_matrices.png"
graph_cm_path = "reports/figures/graph_model_confusion_matrices.png"
threshold_results_path = "reports/metrics/threshold_tuning_results.json"
threshold_curve_path = "reports/figures/threshold_tuning_curve.png"

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Baseline Models",
        "Graph Models",
        "Comparison",
        "Threshold Tuning",
    ]
)

with tab1:
    st.subheader("Baseline Transaction-Only Models")

    if file_exists(baseline_metrics_path):
        baseline_report = load_json_file(baseline_metrics_path)
        baseline_table = extract_model_metric_table(baseline_report)
        st.dataframe(baseline_table, use_container_width=True)

        if file_exists(baseline_cm_path):
            st.image(str(baseline_cm_path))
    else:
        st.warning("Baseline metrics not found. Run `python scripts/train_baseline.py` first.")

with tab2:
    st.subheader("Graph-Enhanced Models")

    if file_exists(graph_metrics_path):
        graph_report = load_json_file(graph_metrics_path)
        graph_table = extract_model_metric_table(graph_report)
        st.dataframe(graph_table, use_container_width=True)

        if file_exists(graph_cm_path):
            st.image(str(graph_cm_path))
    else:
        st.warning("Graph model metrics not found. Run `python scripts/train_graph_model.py` first.")

with tab3:
    st.subheader("Baseline vs Graph-Enhanced Comparison")

    if file_exists(comparison_path):
        comparison_report = load_json_file(comparison_path)
        comparison_table = extract_comparison_table(comparison_report)

        st.dataframe(comparison_table, use_container_width=True)

        best_baseline = comparison_report.get(
            "best_baseline_model_by_average_precision",
            {},
        )
        best_graph = comparison_report.get(
            "best_graph_model_by_average_precision",
            {},
        )

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Best Baseline Model",
                best_baseline.get("model_name", "N/A"),
                best_baseline.get("score", "N/A"),
            )

        with col2:
            st.metric(
                "Best Graph Model",
                best_graph.get("model_name", "N/A"),
                best_graph.get("score", "N/A"),
            )

        if not comparison_table.empty:
            metric_options = sorted(comparison_table["metric"].unique().tolist())
            selected_metric = st.selectbox(
                "Select metric for comparison chart",
                options=metric_options,
                index=metric_options.index("average_precision")
                if "average_precision" in metric_options
                else 0,
            )

            chart_dataframe = comparison_table[
                comparison_table["metric"] == selected_metric
            ][["model", "baseline", "graph_enhanced"]]

            if not chart_dataframe.empty:
                st.bar_chart(chart_dataframe.set_index("model"))
    else:
        st.warning("Comparison report not found. Run `python scripts/train_graph_model.py` first.")

with tab4:
    st.subheader("Threshold Tuning")

    if file_exists(threshold_results_path):
        threshold_report = load_json_file(threshold_results_path)

        best_threshold = threshold_report.get("best_threshold", {})

        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            st.metric("Best Threshold", best_threshold.get("threshold", "N/A"))

        with col_b:
            st.metric("Precision", best_threshold.get("precision", "N/A"))

        with col_c:
            st.metric("Recall", best_threshold.get("recall", "N/A"))

        with col_d:
            st.metric("F1", best_threshold.get("f1", "N/A"))

        threshold_results = threshold_report.get("threshold_results", [])

        if threshold_results:
            threshold_dataframe = pd.DataFrame(threshold_results)
            st.dataframe(threshold_dataframe, use_container_width=True)

        if file_exists(threshold_curve_path):
            st.image(str(threshold_curve_path))
    else:
        st.warning("Threshold tuning results not found. Run `python scripts/tune_threshold.py` first.")