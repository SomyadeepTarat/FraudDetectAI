"""Real migrations, constraints, triggers, rollback, concurrency and API tests.

Set TEST_DATABASE_URL to exercise PostgreSQL as well as SQLite. PostgreSQL tests
use a disposable schema, never drop the configured database or existing tables.
"""

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.api.routes import get_inference
from app.db.models import (
    Account,
    AuditLog,
    BankingTransaction,
    Customer,
    Device,
    FraudAlert,
    FraudPrediction,
)
from app.db.session import get_session, make_engine
from app.main import app
from app.schemas import TransactionCreate
from app.services.demos import concurrency_demo, rollback_demo
from app.services.inference import ModelInference
from app.services.transactions import BankingError, process_transfer
from app.settings import settings


class TestInference:
    __test__ = False

    def __init__(self, probability=0.1):
        self.probability = probability

    def predict(self, transaction):
        return self.probability, "test-model", "test-version"


@pytest.fixture(
    params=["sqlite"] + (["postgresql"] if os.getenv("TEST_DATABASE_URL") else [])
)
def factory(request, tmp_path):
    schema = None
    if request.param == "sqlite":
        engine = make_engine(f"sqlite:///{tmp_path}/banking.db")
    else:
        engine = make_engine(os.environ["TEST_DATABASE_URL"])
        schema = "test_" + uuid4().hex
        with engine.begin() as connection:
            connection.exec_driver_sql(f"CREATE SCHEMA {schema}")
    config = Config("alembic.ini")
    with engine.connect() as connection:
        if schema:
            connection.exec_driver_sql(f"SET search_path TO {schema}")
            connection.commit()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    if schema:
        from sqlalchemy import event

        @event.listens_for(engine, "checkout")
        def search_path(dbapi_connection, _, __):
            with dbapi_connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {schema}")
            dbapi_connection.commit()

    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session, session.begin():
        session.add_all(
            [
                Customer(customer_id="C1", name="Alice", email="alice@example.test"),
                Customer(customer_id="C2", name="Bob", email="bob@example.test"),
            ]
        )
        session.flush()
        session.add_all(
            [
                Account(account_id="A1", customer_id="C1", balance=Decimal(1000000)),
                Account(account_id="A2", customer_id="C2", balance=Decimal(10000)),
            ]
        )
        session.add_all(
            [
                Device(
                    device_id="D1",
                    customer_id="C1",
                    device_identifier="known",
                    trusted=True,
                ),
                Device(
                    device_id="D2",
                    customer_id="C2",
                    device_identifier="other",
                    trusted=True,
                ),
            ]
        )
    yield factory
    if schema:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"DROP SCHEMA {schema} CASCADE")
    engine.dispose()


def transfer(**overrides):
    return TransactionCreate(
        **{
            "customer_id": "C1",
            "account_id": "A1",
            "destination_account_id": "A2",
            "amount": "1000",
            "device_id": "D1",
            "location": "Vellore",
            **overrides,
        }
    )


def test_transfer_prediction_balances_and_audit(factory):
    with factory() as session:
        tx = process_transfer(session, transfer(), TestInference())
        assert session.get(Account, "A1").balance == Decimal(999000)
        assert session.get(Account, "A2").balance == Decimal(11000)
        prediction = session.scalar(
            select(FraudPrediction).where(
                FraudPrediction.transaction_id == tx.transaction_id
            )
        )
        assert prediction.fraud_probability == 0.1
        assert prediction.classification == "NORMAL"
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.record_id == tx.transaction_id)
            )
            >= 1
        )
        assert session.scalar(select(func.count()).select_from(FraudAlert)) == 0


def test_database_trigger_and_audit(factory):
    with factory() as session:
        tx = process_transfer(session, transfer(), TestInference(0.95))
        alert = session.scalar(
            select(FraudAlert).where(FraudAlert.transaction_id == tx.transaction_id)
        )
        assert alert and alert.alert_status == "OPEN"
        alert.alert_status = "INVESTIGATING"
        session.commit()
        log = session.scalar(
            select(AuditLog).where(
                AuditLog.record_id == alert.alert_id, AuditLog.operation == "UPDATE"
            )
        )
        assert log.old_values["alert_status"] == "OPEN"
        assert log.new_values["alert_status"] == "INVESTIGATING"


def test_trigger_fires_for_direct_sql_prediction(factory):
    with factory() as session:
        tx = process_transfer(session, transfer(), TestInference())
        prediction = session.scalar(
            select(FraudPrediction).where(
                FraudPrediction.transaction_id == tx.transaction_id
            )
        )
        session.delete(prediction)
        session.commit()
        session.execute(
            text("""INSERT INTO fraud_predictions (prediction_id, transaction_id, model_name,
            model_version, fraud_probability, behaviour_score, risk_score, classification,
            features, reasons, predicted_at) VALUES (:id, :tx, 'test', '1', 0.85, 0, 0.85,
            'FRAUD', '{}', '[]', CURRENT_TIMESTAMP)"""),
            {"id": "direct", "tx": tx.transaction_id},
        )
        session.commit()
        assert session.scalar(
            select(FraudAlert).where(FraudAlert.prediction_id == "direct")
        )


def test_rollback_after_writes_and_insufficient_balance(factory):
    result = rollback_demo(factory, TestInference())
    assert result["rollback_verified"]
    assert result["before"] == result["after"]


def test_concurrent_debits(factory):
    assert concurrency_demo(factory, TestInference())["concurrency_verified"]


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"customer_id": "missing"}, "Customer not found"),
        ({"account_id": "missing"}, "Account not found"),
        ({"account_id": "A2", "destination_account_id": "A1"}, "does not belong"),
        ({"device_id": "D2"}, "Register"),
        ({"amount": "1000001"}, "Insufficient balance"),
        ({"destination_account_id": "A1"}, "must differ"),
    ],
)
def test_invalid_transfers_do_not_write(factory, changes, message):
    with factory() as session:
        with pytest.raises(BankingError, match=message):
            process_transfer(session, transfer(**changes), TestInference())
        assert session.get(Account, "A1").balance == Decimal(1000000)
        assert session.scalar(select(func.count()).select_from(BankingTransaction)) == 0


def test_constraints_and_foreign_keys(factory):
    for account in [
        Account(customer_id="missing", balance=Decimal(10)),
        Account(customer_id="C1", balance=Decimal(-1)),
    ]:
        with factory() as session:
            session.add(account)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()


def test_ownership_constraint(factory):
    with factory() as session:
        tx = process_transfer(session, transfer(), TestInference())
        tx.customer_id = "C2"
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_customer_update_audit_redacts_contacts(factory):
    with factory() as session:
        session.get(Customer, "C1").status = "BLOCKED"
        session.commit()
        log = session.scalar(
            select(AuditLog).where(
                AuditLog.table_name == "customers", AuditLog.operation == "UPDATE"
            )
        )
        assert log.old_values == {"status": "ACTIVE"}
        assert log.new_values == {"status": "BLOCKED"}


def test_burst_rules_use_sql_history(factory):
    for _ in range(25):
        with factory() as session:
            tx = process_transfer(session, transfer(amount="10"), TestInference())
    with factory() as session:
        prediction = session.scalar(
            select(FraudPrediction).where(
                FraudPrediction.transaction_id == tx.transaction_id
            )
        )
        assert prediction.features["transaction_count_last_10_minutes"] == 25
        assert prediction.fraud_probability == 0.1
        assert prediction.risk_score >= 0.8
        assert prediction.classification == "SUSPICIOUS"
        assert session.scalar(
            select(FraudAlert).where(FraudAlert.transaction_id == tx.transaction_id)
        )


def test_api_major_endpoints(factory):
    def dependency():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = dependency
    app.dependency_overrides[get_inference] = lambda: TestInference(0.95)
    try:
        with TestClient(app) as client:
            assert client.get("/customers").status_code == 200
            assert (
                client.post(
                    "/customers",
                    json={
                        "customer_id": "C3",
                        "name": "Carol",
                        "email": "carol@example.test",
                    },
                ).status_code
                == 201
            )
            assert (
                client.post(
                    "/accounts", json={"customer_id": "C3", "balance": "100"}
                ).status_code
                == 201
            )
            response = client.post(
                "/transactions", json=transfer().model_dump(mode="json")
            )
            assert response.status_code == 201, response.text
            transaction_id = response.json()["transaction_id"]
            assert (
                client.get(f"/transactions/{transaction_id}/prediction").json()[
                    "fraud_probability"
                ]
                == 0.95
            )
            for path in [
                "/transactions",
                f"/transactions/{transaction_id}",
                "/fraud/statistics",
                "/fraud/suspicious-transactions",
                "/audit-logs",
                "/database/overview",
                "/customers/C1/transactions",
                "/customers/C1/risk-summary",
                "/devices",
                "/accounts",
            ]:
                assert client.get(path).status_code == 200, path
            alert = client.get("/fraud/alerts").json()[0]
            assert (
                client.patch(
                    f"/fraud/alerts/{alert['alert_id']}",
                    json={"alert_status": "RESOLVED", "reviewed_by": "tester"},
                ).status_code
                == 200
            )
            assert (
                client.get("/fraud/statistics").json()["confirmed_fraud_transactions"]
                == 1
            )
            assert (
                client.post(
                    "/transactions",
                    json={**transfer().model_dump(mode="json"), "amount": "-1"},
                ).status_code
                == 422
            )
            assert (
                client.post(
                    "/customers",
                    json={"name": "Duplicate", "email": "alice@example.test"},
                ).status_code
                == 409
            )
            assert client.get("/transactions/missing").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_real_existing_model_inference(factory):
    model = ModelInference(settings.model_path)
    if not model.path.exists():
        pytest.skip(
            "Run scripts/train_banking_model.py or the existing baseline training pipeline"
        )
    with factory() as session:
        tx = process_transfer(session, transfer(), model)
        prediction = session.scalar(
            select(FraudPrediction).where(
                FraudPrediction.transaction_id == tx.transaction_id
            )
        )
        assert 0 <= prediction.fraud_probability <= 1
        assert len(prediction.model_version) == 64


def test_postgres_functions(factory):
    with factory() as session:
        if session.bind.dialect.name != "postgresql":
            pytest.skip("Stored SQL functions require PostgreSQL")
        process_transfer(session, transfer(), TestInference())
        assert (
            session.execute(
                text("SELECT calculate_transaction_velocity('C1', 10)")
            ).scalar_one()
            == 1
        )
        assert (
            session.execute(
                text(
                    "SELECT total_transactions FROM get_customer_transaction_stats('C1')"
                )
            ).scalar_one()
            == 1
        )


def test_dashboard_transfer_and_audit_inspection(factory, monkeypatch):
    """Exercise Streamlit pages against the migrated API, including a form submit."""
    from pathlib import Path

    import httpx
    from streamlit.testing.v1 import AppTest

    def dependency():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = dependency
    app.dependency_overrides[get_inference] = lambda: TestInference(0.95)
    try:
        with TestClient(app) as client:
            monkeypatch.setattr(
                httpx,
                "request",
                lambda method, url, **kwargs: client.request(method, url, **kwargs),
            )
            banking = AppTest.from_file(
                Path(__file__).resolve().parents[1] / "app/pages/Banking.py"
            ).run(timeout=20)
            assert not banking.exception
            assert not banking.error
            next(
                x for x in banking.selectbox if x.label == "Destination account"
            ).set_value("A2")
            next(x for x in banking.button if x.label == "Process transfer").click()
            banking.run(timeout=20)
            assert not banking.exception
            assert not banking.error
            assert any("Committed" in x.value for x in banking.success)
            dbms = AppTest.from_file(
                Path(__file__).resolve().parents[1] / "app/pages/DBMS_Demonstration.py"
            ).run(timeout=20)
            assert not dbms.exception
            assert not dbms.error
            assert len(dbms.json) >= 2  # Schema metadata and old/new audit payload.
    finally:
        app.dependency_overrides.clear()


def test_migrations_downgrade_and_upgrade(factory):
    engine = factory.kw["bind"]
    config = Config("alembic.ini")
    # Remove all data only in this test's disposable database/schema.
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        assert (
            connection.execute(text("SELECT COUNT(*) FROM risk_settings")).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM customer_risk_summary")
            ).scalar_one()
            == 0
        )
