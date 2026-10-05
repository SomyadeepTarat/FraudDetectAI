"""One database transaction covers balances, inference, prediction and triggers."""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import (
    Account,
    BankingTransaction,
    Customer,
    Device,
    FraudPrediction,
    RiskSettings,
    utcnow,
)
from app.schemas import TransactionCreate
from app.services.features import behaviour_features, behaviour_risk


class Inference(Protocol):
    def predict(self, transaction: BankingTransaction) -> tuple[float, str, str]: ...


class BankingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def process_transfer(
    session: Session,
    request: TransactionCreate,
    inference: Inference,
    *,
    timestamp: datetime | None = None,
) -> BankingTransaction:
    """Caller must pass a fresh session. Errors roll back every banking write."""
    if session.in_transaction():
        raise RuntimeError("process_transfer requires a fresh transaction boundary")
    with session.begin():
        if session.bind.dialect.name == "sqlite":
            # SQLite has no row locks. Take its database writer lock before reads.
            session.execute(text("BEGIN IMMEDIATE"))
        else:
            session.execute(
                text("SELECT set_config('app.actor', :actor, true)"),
                {"actor": "transaction-service"},
            )
        # Serializes all accounts of a customer for consistent velocity queries.
        customer = session.scalar(
            select(Customer)
            .where(Customer.customer_id == request.customer_id)
            .with_for_update()
        )
        if not customer:
            raise BankingError("Customer not found", 404)
        if customer.status != "ACTIVE":
            raise BankingError("Customer is not active", 409)
        if request.account_id == request.destination_account_id:
            raise BankingError("Source and destination must differ")
        # Global account ordering avoids deadlocks for opposite-direction transfers.
        accounts = session.scalars(
            select(Account)
            .where(
                Account.account_id.in_(
                    [
                        request.account_id,
                        request.destination_account_id,
                    ]
                )
            )
            .order_by(Account.account_id)
            .with_for_update()
        ).all()
        by_id = {account.account_id: account for account in accounts}
        if len(by_id) != 2:
            raise BankingError("Account not found", 404)
        source = by_id[request.account_id]
        destination = by_id[request.destination_account_id]
        if source.customer_id != customer.customer_id:
            raise BankingError("Account does not belong to customer", 409)
        if source.status != "ACTIVE" or destination.status != "ACTIVE":
            raise BankingError("Both accounts must be active", 409)
        if source.currency != destination.currency:
            raise BankingError("Cross-currency transfers are not supported")
        if source.balance < request.amount:
            raise BankingError("Insufficient balance", 409)
        if request.device_id:
            device = session.scalar(
                select(Device)
                .where(Device.device_id == request.device_id)
                .with_for_update()
            )
            if not device or device.customer_id != customer.customer_id:
                raise BankingError(
                    "Register the customer's device before transacting", 409
                )
        else:
            device = None
        transaction = BankingTransaction(
            **request.model_dump(),
            transaction_timestamp=timestamp or utcnow(),
            balance_before=source.balance,
            balance_after=source.balance - request.amount,
            destination_balance_before=destination.balance,
            destination_balance_after=destination.balance + request.amount,
            status="COMPLETED",
        )
        source.balance = transaction.balance_after
        destination.balance = transaction.destination_balance_after
        session.add(transaction)
        session.flush()
        features = behaviour_features(session, transaction)
        behaviour, reasons = behaviour_risk(features)
        try:
            probability, model_name, model_version = inference.predict(transaction)
        except Exception as exc:
            raise BankingError(
                "Model inference failed; transfer rolled back. Check MODEL_PATH and train a baseline model.",
                503,
            ) from exc
        # Rule risk is a heuristic, not a calibrated probability. Preserve ML output.
        risk = max(probability, 0.9 * behaviour)
        # Shared PostgreSQL lock keeps classification and the INSERT trigger on
        # the same threshold even if an administrator changes it concurrently.
        risk_settings = session.scalar(
            select(RiskSettings)
            .where(RiskSettings.settings_id == 1)
            .with_for_update(read=True)
        )
        if risk_settings is None:
            raise BankingError("Database risk settings missing; run migrations", 503)
        threshold = risk_settings.fraud_threshold
        classification = (
            "FRAUD"
            if probability >= threshold
            else "SUSPICIOUS"
            if risk >= threshold
            else "NORMAL"
        )
        if classification != "NORMAL":
            transaction.status = "FLAGGED"
        if probability >= threshold:
            reasons.append("ML probability exceeds fraud threshold")
        prediction = FraudPrediction(
            transaction_id=transaction.transaction_id,
            model_name=model_name,
            model_version=model_version,
            fraud_probability=probability,
            behaviour_score=behaviour,
            risk_score=risk,
            classification=classification,
            features=features,
            reasons=reasons,
        )
        session.add(prediction)
        if device:
            device.last_seen = transaction.transaction_timestamp
        session.flush()  # DB creates the alert and audit records here.
    return transaction
