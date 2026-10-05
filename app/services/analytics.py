from sqlalchemy import func, inspect, select, text

from app.db.models import Account, Customer, Device, FraudAlert
from app.db.models import BankingTransaction as T
from app.db.models import FraudPrediction as P


def record(entity):
    return {
        column.key: getattr(entity, column.key)
        for column in inspect(entity).mapper.column_attrs
    }


def transaction_query():
    return (
        select(T, P, Customer.name)
        .join(Customer, Customer.customer_id == T.customer_id)
        .outerjoin(P, P.transaction_id == T.transaction_id)
    )


def transaction_record(row):
    transaction, prediction, name = row
    return {
        **record(transaction),
        "customer_name": name,
        "prediction": record(prediction) if prediction else None,
    }


def statistics(session):
    row = session.execute(
        select(
            func.count(T.transaction_id),
            func.coalesce(func.sum(T.amount), 0),
            func.coalesce(func.avg(P.risk_score), 0),
        ).outerjoin(P, P.transaction_id == T.transaction_id)
    ).one()
    return {
        "total_transactions": row[0],
        "total_transaction_amount": row[1],
        "average_fraud_risk": row[2],
        "suspicious_transactions": session.scalar(
            select(func.count()).select_from(P).where(P.classification != "NORMAL")
        ),
        "confirmed_fraud_transactions": session.scalar(
            select(func.count())
            .select_from(FraudAlert)
            .where(FraudAlert.alert_status == "RESOLVED")
        ),
        "model_classified_fraud": session.scalar(
            select(func.count()).select_from(P).where(P.classification == "FRAUD")
        ),
        "open_alerts": session.scalar(
            select(func.count())
            .select_from(FraudAlert)
            .where(FraudAlert.alert_status.in_(["OPEN", "INVESTIGATING"]))
        ),
    }


def customer_summary(session, customer_id):
    summary = (
        session.execute(
            text("SELECT * FROM customer_risk_summary WHERE customer_id = :customer"),
            {"customer": customer_id},
        )
        .mappings()
        .first()
    )
    if summary is None:
        return None
    return {
        **dict(summary),
        "accounts": [
            record(x)
            for x in session.scalars(
                select(Account).where(Account.customer_id == customer_id)
            )
        ],
        "devices": [
            record(x)
            for x in session.scalars(
                select(Device).where(Device.customer_id == customer_id)
            )
        ],
    }


def index_plan(session, customer_id):
    sql = "SELECT COUNT(*) FROM transactions WHERE customer_id = :customer AND transaction_timestamp >= :since"
    from datetime import timedelta

    from app.db.models import utcnow

    prefix = (
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
        if session.bind.dialect.name == "postgresql"
        else "EXPLAIN QUERY PLAN "
    )
    rows = session.execute(
        text(prefix + sql),
        {"customer": customer_id, "since": utcnow() - timedelta(minutes=10)},
    ).all()
    return {
        "dialect": session.bind.dialect.name,
        "query": sql,
        "plan": [list(row) for row in rows],
        "note": "Small tables may use a sequential scan; the plan is measured, not a promised speedup.",
    }


def database_overview(session):
    inspector = inspect(session.bind)
    if session.bind.dialect.name == "postgresql":
        triggers = (
            session.execute(
                text(
                    "SELECT trigger_name, event_object_table, event_manipulation FROM information_schema.triggers WHERE trigger_schema = current_schema() ORDER BY trigger_name"
                )
            )
            .mappings()
            .all()
        )
        functions = (
            session.execute(
                text(
                    "SELECT routine_name FROM information_schema.routines WHERE routine_schema = current_schema() AND routine_name IN ('get_customer_transaction_stats','calculate_transaction_velocity')"
                )
            )
            .scalars()
            .all()
        )
    else:
        triggers = (
            session.execute(
                text(
                    "SELECT name AS trigger_name, tbl_name AS event_object_table, sql FROM sqlite_master WHERE type = 'trigger'"
                )
            )
            .mappings()
            .all()
        )
        functions = []
    return {
        "dialect": session.bind.dialect.name,
        "tables": inspector.get_table_names(),
        "indexes": {
            table: inspector.get_indexes(table) for table in inspector.get_table_names()
        },
        "views": inspector.get_view_names(),
        "triggers": [dict(x) for x in triggers],
        "stored_functions": functions,
        "threshold": session.execute(
            text("SELECT fraud_threshold FROM risk_settings WHERE settings_id = 1")
        ).scalar_one(),
        "isolation": session.connection().get_isolation_level(),
    }
