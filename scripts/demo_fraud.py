"""Normal, high amount, new device, burst, trigger and audit demonstrations."""

import json
from decimal import Decimal

from sqlalchemy import select

from app.db.models import AuditLog, FraudAlert, FraudPrediction, utcnow
from app.db.session import SessionLocal
from app.schemas import TransactionCreate
from app.services.analytics import record
from app.services.inference import ModelInference
from app.services.transactions import process_transfer
from app.settings import settings


def main():
    model = ModelInference(settings.model_path)
    scenarios = [
        ("normal", "4500", "D001", "Vellore"),
        ("new device", "4500", "D901", "Vellore"),
        ("high amount / new location", "85000", "D901", "Delhi"),
    ]
    scenarios += [(f"burst {i + 1}/25", "100", "D901", "Delhi") for i in range(25)]
    for label, amount, device, location in scenarios:
        request = TransactionCreate(
            customer_id="C001",
            account_id="A001",
            destination_account_id="A002",
            amount=Decimal(amount),
            device_id=device,
            location=location,
        )
        with SessionLocal() as session:
            transaction = process_transfer(session, request, model)
            prediction = session.scalar(
                select(FraudPrediction).where(
                    FraudPrediction.transaction_id == transaction.transaction_id
                )
            )
            alert = session.scalar(
                select(FraudAlert).where(
                    FraudAlert.transaction_id == transaction.transaction_id
                )
            )
            print(
                json.dumps(
                    {
                        "scenario": label,
                        "transaction_id": transaction.transaction_id,
                        "prediction": record(prediction),
                        "trigger_created_alert": bool(alert),
                    },
                    default=str,
                )
            )
    with SessionLocal() as session, session.begin():
        alert = session.scalar(
            select(FraudAlert)
            .order_by(FraudAlert.created_at.desc())
            .limit(1)
            .with_for_update()
        )
        if alert:
            alert.alert_status = "INVESTIGATING"
            alert.reviewed_by = "university-demo"
            alert.reviewed_at = utcnow()
            session.flush()
            logs = session.scalars(
                select(AuditLog).where(
                    AuditLog.record_id == alert.alert_id, AuditLog.operation == "UPDATE"
                )
            ).all()
            print(
                json.dumps({"audit_update": [record(log) for log in logs]}, default=str)
            )


if __name__ == "__main__":
    main()
