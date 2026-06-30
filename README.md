# FraudGraph AI

FraudGraph AI is a graph-based financial fraud detection project that models transaction data as a sender-receiver network and uses machine learning to identify suspicious transactions.

## Project Goal

The goal of this project is to compare traditional transaction-level fraud detection with graph-enhanced fraud detection.

Traditional models look only at individual transaction features such as amount, transaction type, and balance changes. FraudGraph AI adds graph-based features such as sender degree, receiver degree, transaction network behavior, and account connectivity patterns.

## Planned Features

- Data cleaning and validation pipeline
- Exploratory data analysis
- Baseline fraud detection models
- Transaction graph construction
- Graph-based feature engineering
- Model comparison using fraud-specific metrics
- Explainability using feature importance and SHAP
- Streamlit dashboard for fraud investigation
- Optional Graph Neural Network extension

## Tech Stack

- Python
- pandas
- scikit-learn
- XGBoost
- NetworkX
- SHAP
- Streamlit
- pytest

## Dataset

The project is designed around the PaySim mobile money fraud dataset.

Place the raw CSV file inside:

```text
data/raw/