"""Deterministic synthetic banking metadata; every prediction uses the real model."""

import argparse
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.db.models import Account, Customer, Device, utcnow
from app.db.session import SessionLocal
from app.schemas import TransactionCreate
from app.services.inference import ModelInference
from app.services.transactions import process_transfer
from app.settings import settings


def seed(factory=SessionLocal, transaction_count=400):
    model = ModelInference(settings.model_path)
    _ = model.model  # Fail before populating if no artifact exists.
    with factory() as session, session.begin():
        if session.scalar(select(func.count()).select_from(Customer)):
            print("Database already contains customers; seed skipped.")
            return
        session.add_all(
            [
                Customer(
                    customer_id=f"C{i:03}",
                    name=f"Demo Customer {i}",
                    email=f"customer{i}@demo.example",
                )
                for i in range(1, 21)
            ]
        )
        session.flush()
        session.add_all(
            [
                Account(
                    account_id=f"A{i:03}",
                    customer_id=f"C{((i - 1) % 20) + 1:03}",
                    balance=Decimal(10000000),
                    currency="INR",
                )
                for i in range(1, 31)
            ]
        )
        session.add_all(
            [
                Device(
                    device_id=f"D{i:03}",
                    customer_id=f"C{i:03}",
                    device_identifier=f"demo-trusted-{i}",
                    trusted=True,
                )
                for i in range(1, 21)
            ]
        )
        session.add(
            Device(
                device_id="D901",
                customer_id="C001",
                device_identifier="demo-new-901",
                trusted=False,
            )
        )
        session.add(
            Device(
                device_id="D920",
                customer_id="C020",
                device_identifier="demo-new-920",
                trusted=False,
            )
        )
    now = utcnow().replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(
        days=1
    )
    for i in range(transaction_count):
        owner = i % 20 + 1
        request = TransactionCreate(
            customer_id=f"C{owner:03}",
            account_id=f"A{owner:03}",
            destination_account_id=f"A{owner % 20 + 1:03}",
            amount=Decimal(3500 + (i % 5) * 500),
            device_id=f"D{owner:03}",
            location="Vellore",
        )
        # Three transfers/day per customer spread over past days.
        timestamp = now - timedelta(
            days=(transaction_count - 1 - i) // 60, hours=(i // 20) % 3
        )
        with factory() as session:
            process_transfer(session, request, model, timestamp=timestamp)
    # Seed suspicious scenarios for C020, leaving C001 available for a clean live demo.
    for i in range(26):
        request = TransactionCreate(
            customer_id="C020",
            account_id="A020",
            destination_account_id="A001",
            amount="85000" if i == 0 else "100",
            device_id="D920",
            location="Delhi",
        )
        with factory() as session:
            process_transfer(session, request, model)
    print(
        f"Seeded 20 customers, 30 accounts, 22 devices and {transaction_count + 26} model-scored transfers, including high-amount/new-device/location and burst scenarios. Metadata and transfer patterns are synthetic."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transactions", type=int, default=400)
    args = parser.parse_args()
    seed(transaction_count=args.transactions)
