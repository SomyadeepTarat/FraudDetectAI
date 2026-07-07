import pandas as pd
import streamlit as st

from dashboard_utils import file_exists, load_json_file


st.set_page_config(
    page_title="Explainability | FraudGraph AI",
    page_icon="🔎",
    layout="wide",
)

st.title(" Explainability")

feature_importance_report_path = "reports/metrics/feature_importance_report.json"
feature_importance_plot_path = "reports/figures/top_feature_importance.png"
transaction_explanations_path = "reports/metrics/top_risky_transaction_explanations.json"

tab1, tab2 = st.tabs(["Global Feature Importance", "Transaction Explanations"])

with tab1:
    st.subheader("Global Feature Importance")

    if file_exists(feature_importance_report_path):
        feature_report = load_json_file(feature_importance_report_path)
        feature_rows = feature_report.get("features", [])

        if feature_rows:
            feature_dataframe = pd.DataFrame(feature_rows)
            st.dataframe(feature_dataframe, use_container_width=True)
        else:
            st.info("No feature importance rows available.")

        if file_exists(feature_importance_plot_path):
            st.image(str(feature_importance_plot_path))
        else:
            st.warning("Feature importance plot not found.")
    else:
        st.warning("Feature importance report not found. Run `python scripts/explain_model.py` first.")

with tab2:
    st.subheader("Top Risky Transaction Explanations")

    if file_exists(transaction_explanations_path):
        explanation_report = load_json_file(transaction_explanations_path)
        explanations = explanation_report.get("explanations", [])

        if not explanations:
            st.info("No transaction explanations available.")
        else:
            for explanation in explanations:
                with st.expander(
                    f"Rank {explanation.get('rank')} | "
                    f"{explanation.get('risk_band')} | "
                    f"Probability {explanation.get('fraud_probability'):.4f} | "
                    f"{explanation.get('transaction_type')}"
                ):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.write(f"**Sender:** {explanation.get('sender')}")
                        st.write(f"**Receiver:** {explanation.get('receiver')}")

                    with col2:
                        st.write(f"**Amount:** {explanation.get('amount')}")
                        st.write(f"**Predicted Fraud:** {explanation.get('predicted_fraud')}")

                    with col3:
                        st.write(f"**Actual Fraud:** {explanation.get('actual_is_fraud')}")
                        st.write(f"**Risk Band:** {explanation.get('risk_band')}")

                    st.write("**Reasons:**")
                    for reason in explanation.get("reasons", []):
                        st.write(f"- {reason}")
    else:
        st.warning("Transaction explanations not found. Run `python scripts/explain_model.py` first.")