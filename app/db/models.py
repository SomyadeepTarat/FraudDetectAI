"""Banking entities. Monetary values use fixed precision, never binary floats."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


json_type = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    customer_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=new_id
    )
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(
        String(20), default="ACTIVE", server_default="ACTIVE"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE','BLOCKED','UNDER_REVIEW')", name="ck_customer_status"
        ),
    )


class Account(Base):
    __tablename__ = "accounts"
    account_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=new_id
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id"), index=True
    )
    account_type: Mapped[str] = mapped_column(String(20), default="SAVINGS")
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        UniqueConstraint("account_id", "customer_id", name="uq_account_owner"),
        CheckConstraint("balance >= 0", name="ck_account_balance"),
        CheckConstraint(
            "status IN ('ACTIVE','BLOCKED','CLOSED')", name="ck_account_status"
        ),
        CheckConstraint(
            "account_type IN ('SAVINGS','CURRENT')", name="ck_account_type"
        ),
        CheckConstraint("length(currency) = 3", name="ck_currency"),
    )


class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id"), index=True
    )
    device_type: Mapped[str] = mapped_column(String(30), default="MOBILE")
    device_identifier: Mapped[str] = mapped_column(String(120), unique=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        UniqueConstraint("device_id", "customer_id", name="uq_device_owner"),
    )


class BankingTransaction(Base):
    __tablename__ = "transactions"
    transaction_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=new_id
    )
    account_id: Mapped[str] = mapped_column(String(64))
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    destination_account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.account_id")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    transaction_type: Mapped[str] = mapped_column(String(20), default="TRANSFER")
    payment_method: Mapped[str] = mapped_column(String(20), default="UPI")
    transaction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    location: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    device_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    balance_before: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    destination_balance_before: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    destination_balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "customer_id"],
            ["accounts.account_id", "accounts.customer_id"],
            name="fk_transaction_owner",
        ),
        ForeignKeyConstraint(
            ["device_id", "customer_id"],
            ["devices.device_id", "devices.customer_id"],
            name="fk_transaction_device_owner",
        ),
        CheckConstraint("amount > 0", name="ck_transaction_amount"),
        CheckConstraint(
            "account_id <> destination_account_id", name="ck_different_accounts"
        ),
        CheckConstraint("transaction_type = 'TRANSFER'", name="ck_transaction_type"),
        CheckConstraint(
            "status IN ('PENDING','COMPLETED','FAILED','FLAGGED')",
            name="ck_transaction_status",
        ),
        CheckConstraint(
            "balance_before >= 0 AND balance_after >= 0 AND destination_balance_before >= 0 AND destination_balance_after >= 0",
            name="ck_transaction_balances",
        ),
        CheckConstraint(
            "balance_after = balance_before - amount AND destination_balance_after = destination_balance_before + amount",
            name="ck_transfer_snapshots",
        ),
        CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90", name="ck_latitude"
        ),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180", name="ck_longitude"
        ),
        Index(
            "idx_transactions_customer_timestamp",
            "customer_id",
            "transaction_timestamp",
        ),
        Index(
            "idx_transactions_account_timestamp", "account_id", "transaction_timestamp"
        ),
    )


class FraudPrediction(Base):
    __tablename__ = "fraud_predictions"
    prediction_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=new_id
    )
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.transaction_id"), unique=True
    )
    model_name: Mapped[str] = mapped_column(String(120))
    model_version: Mapped[str] = mapped_column(String(64))
    fraud_probability: Mapped[float]
    behaviour_score: Mapped[float]
    risk_score: Mapped[float]
    classification: Mapped[str] = mapped_column(String(20))
    features: Mapped[dict] = mapped_column(json_type)
    reasons: Mapped[list] = mapped_column(json_type)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    __table_args__ = (
        UniqueConstraint(
            "prediction_id", "transaction_id", name="uq_prediction_transaction"
        ),
        CheckConstraint(
            "fraud_probability BETWEEN 0 AND 1 AND behaviour_score BETWEEN 0 AND 1 AND risk_score BETWEEN 0 AND 1",
            name="ck_prediction_scores",
        ),
        CheckConstraint(
            "classification IN ('NORMAL','SUSPICIOUS','FRAUD')",
            name="ck_classification",
        ),
        Index("idx_fraud_predictions_risk", "risk_score"),
    )


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"
    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.transaction_id")
    )
    prediction_id: Mapped[str] = mapped_column(String(64), unique=True)
    risk_score: Mapped[float]
    reason: Mapped[str] = mapped_column(String(500))
    alert_status: Mapped[str] = mapped_column(
        String(20), default="OPEN", server_default="OPEN"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    __table_args__ = (
        ForeignKeyConstraint(
            ["prediction_id", "transaction_id"],
            ["fraud_predictions.prediction_id", "fraud_predictions.transaction_id"],
            name="fk_alert_prediction_transaction",
        ),
        CheckConstraint(
            "alert_status IN ('OPEN','INVESTIGATING','RESOLVED','FALSE_POSITIVE')",
            name="ck_alert_status",
        ),
        CheckConstraint("risk_score BETWEEN 0 AND 1", name="ck_alert_risk"),
        Index("idx_alert_status", "alert_status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    table_name: Mapped[str] = mapped_column(String(64))
    record_id: Mapped[str] = mapped_column(String(64))
    operation: Mapped[str] = mapped_column(String(10))
    old_values: Mapped[dict | None] = mapped_column(json_type)
    new_values: Mapped[dict | None] = mapped_column(json_type)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    changed_by: Mapped[str] = mapped_column(String(120), default="database")
    __table_args__ = (
        CheckConstraint(
            "operation IN ('INSERT','UPDATE','DELETE')", name="ck_audit_operation"
        ),
    )


class RiskSettings(Base):
    __tablename__ = "risk_settings"
    settings_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fraud_threshold: Mapped[float]
    __table_args__ = (
        CheckConstraint("settings_id = 1", name="ck_single_settings"),
        CheckConstraint(
            "fraud_threshold > 0 AND fraud_threshold < 1", name="ck_fraud_threshold"
        ),
    )
