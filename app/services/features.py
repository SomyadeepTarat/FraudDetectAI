"""SQL aggregates for application behaviour; these are not PaySim attributes."""

from datetime import timedelta

from sqlalchemy import case, func, select

from app.db.models import BankingTransaction as T
from app.db.models import Device


def behaviour_features(session, transaction):
    now = transaction.transaction_timestamp
    historical = [
        T.customer_id == transaction.customer_id,
        T.transaction_id != transaction.transaction_id,
        T.transaction_timestamp <= now,
        T.status.in_(["COMPLETED", "FLAGGED"]),
    ]
    row = session.execute(
        select(
            func.count(T.transaction_id).label("total"),
            func.avg(T.amount).label("average"),
            func.max(
                case((T.transaction_timestamp >= now - timedelta(days=30), T.amount))
            ).label("max30"),
            func.sum(
                case(
                    (T.transaction_timestamp >= now - timedelta(minutes=10), 1), else_=0
                )
            ).label("count10"),
            func.sum(
                case((T.transaction_timestamp >= now - timedelta(hours=1), 1), else_=0)
            ).label("count60"),
            func.sum(
                case((T.transaction_timestamp >= now - timedelta(days=1), 1), else_=0)
            ).label("count24"),
            func.min(T.transaction_timestamp).label("first"),
        ).where(*historical)
    ).one()
    previous = session.scalars(
        select(T)
        .where(*historical)
        .order_by(T.transaction_timestamp.desc(), T.transaction_id)
        .limit(1)
    ).first()
    device = (
        session.get(Device, transaction.device_id) if transaction.device_id else None
    )
    average = float(row.average or 0)
    days = max(1, (now.date() - row.first.date()).days + 1) if row.first else 1
    time_since = None
    if previous:
        time_since = max(
            0,
            (
                now.replace(tzinfo=None)
                - previous.transaction_timestamp.replace(tzinfo=None)
            ).total_seconds(),
        )
    return {
        "average_transaction_amount": average,
        "max_transaction_amount_last_30_days": float(row.max30 or 0),
        "transaction_count_last_10_minutes": int(row.count10 or 0) + 1,
        "transaction_count_last_hour": int(row.count60 or 0) + 1,
        "transaction_count_last_24_hours": int(row.count24 or 0) + 1,
        "average_daily_transaction_count": int(row.total) / days,
        "amount_deviation_from_customer_average": float(transaction.amount) / average
        if average
        else None,
        "time_since_previous_transaction": time_since,
        "is_new_device": bool(
            transaction.device_id and (not device or not device.trusted)
        ),
        "location_changed": bool(
            previous
            and previous.location
            and transaction.location
            and previous.location != transaction.location
        ),
        "unusual_transaction_hour": now.hour
        < 6,  # UTC, not a claim about customer timezone
        "metadata_source": "application/demo; device/location are not PaySim fields",
    }


def behaviour_risk(features):
    score = 0.0
    reasons = []
    rules = [
        (
            features["transaction_count_last_10_minutes"] >= 20,
            1.0,
            "20 or more transactions in ten minutes",
        ),
        (
            features["transaction_count_last_10_minutes"] >= 10,
            0.5,
            "Elevated transaction velocity",
        ),
        (
            (features["amount_deviation_from_customer_average"] or 0) >= 10,
            0.9,
            "Amount exceeds ten times historical average",
        ),
        (
            (features["amount_deviation_from_customer_average"] or 0) >= 3,
            0.3,
            "Amount exceeds three times historical average",
        ),
        (features["is_new_device"], 0.2, "Untrusted device"),
        (features["location_changed"], 0.2, "Location changed"),
        (features["unusual_transaction_hour"], 0.1, "Transfer before 06:00 UTC"),
    ]
    for matches, weight, reason in rules:
        if matches:
            score += weight
            reasons.append(reason)
    return min(1.0, score), reasons
