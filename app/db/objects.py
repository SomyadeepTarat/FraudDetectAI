"""Real database triggers and views, installed by the Alembic migration."""

# Only these fields enter the audit trail; contact details, IPs and device IDs do not.
AUDITED = {
    "customers": ("customer_id", ["status"]),
    "accounts": ("account_id", ["balance", "status"]),
    "transactions": (
        "transaction_id",
        ["amount", "status", "account_id", "destination_account_id"],
    ),
    "fraud_predictions": (
        "prediction_id",
        ["transaction_id", "fraud_probability", "risk_score", "classification"],
    ),
    "fraud_alerts": (
        "alert_id",
        ["transaction_id", "alert_status", "risk_score", "reviewed_by"],
    ),
}

VIEWS = {
    "suspicious_transactions_view": """
        SELECT t.transaction_id, t.customer_id, c.name AS customer_name,
               t.amount, p.fraud_probability, p.behaviour_score, p.risk_score,
               p.classification, t.transaction_timestamp, a.alert_status
        FROM transactions t JOIN customers c ON c.customer_id = t.customer_id
        JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        LEFT JOIN fraud_alerts a ON a.prediction_id = p.prediction_id
        WHERE p.classification <> 'NORMAL'
    """,
    "customer_risk_summary": """
        SELECT c.customer_id, c.name, COUNT(t.transaction_id) AS total_transactions,
               SUM(CASE WHEN p.classification <> 'NORMAL' THEN 1 ELSE 0 END) AS suspicious_transactions,
               COALESCE(AVG(t.amount), 0) AS average_transaction_amount,
               COALESCE(MAX(p.risk_score), 0) AS maximum_risk_score,
               MAX(CASE WHEN p.classification <> 'NORMAL' THEN t.transaction_timestamp END) AS latest_suspicious_transaction
        FROM customers c LEFT JOIN transactions t ON t.customer_id = c.customer_id
        LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        GROUP BY c.customer_id, c.name
    """,
}


def install_objects(connection):
    postgres = connection.dialect.name == "postgresql"
    if postgres:
        connection.exec_driver_sql("""
            CREATE FUNCTION create_fraud_alert() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.risk_score >= (SELECT fraud_threshold FROM risk_settings WHERE settings_id = 1) THEN
                    INSERT INTO fraud_alerts (alert_id, transaction_id, prediction_id,
                        risk_score, reason, alert_status, created_at)
                    VALUES ('alert-' || NEW.prediction_id, NEW.transaction_id, NEW.prediction_id,
                        NEW.risk_score, 'Risk threshold exceeded; inspect prediction reasons', 'OPEN', CURRENT_TIMESTAMP);
                END IF;
                RETURN NEW;
            END $$
        """)
        connection.exec_driver_sql(
            "CREATE TRIGGER prediction_alert AFTER INSERT ON fraud_predictions FOR EACH ROW EXECUTE FUNCTION create_fraud_alert()"
        )
    else:
        connection.exec_driver_sql("""
            CREATE TRIGGER prediction_alert AFTER INSERT ON fraud_predictions
            WHEN NEW.risk_score >= (SELECT fraud_threshold FROM risk_settings WHERE settings_id = 1)
            BEGIN
                INSERT INTO fraud_alerts (alert_id, transaction_id, prediction_id,
                    risk_score, reason, alert_status, created_at)
                VALUES ('alert-' || NEW.prediction_id, NEW.transaction_id, NEW.prediction_id,
                    NEW.risk_score, 'Risk threshold exceeded; inspect prediction reasons', 'OPEN', CURRENT_TIMESTAMP);
            END
        """)
    for table, (key, columns) in AUDITED.items():
        if postgres:

            def values(prefix, columns=columns):
                return (
                    "jsonb_build_object("
                    + ", ".join(f"'{col}', {prefix}.{col}" for col in columns)
                    + ")"
                )

            connection.exec_driver_sql(f"""
                CREATE FUNCTION audit_{table}() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    INSERT INTO audit_logs (audit_id, table_name, record_id, operation,
                        old_values, new_values, changed_at, changed_by)
                    VALUES (md5(random()::text || clock_timestamp()::text), '{table}',
                        COALESCE(NEW.{key}, OLD.{key}), TG_OP,
                        CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE {values("OLD")} END,
                        CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE {values("NEW")} END,
                        CURRENT_TIMESTAMP, COALESCE(NULLIF(current_setting('app.actor', true), ''), current_user));
                    RETURN COALESCE(NEW, OLD);
                END $$
            """)
            connection.exec_driver_sql(
                f"CREATE TRIGGER audit_{table} AFTER INSERT OR UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION audit_{table}()"
            )
        else:

            def values(prefix, columns=columns):
                return (
                    "json_object("
                    + ", ".join(f"'{col}', {prefix}.{col}" for col in columns)
                    + ")"
                )

            for operation in ("INSERT", "UPDATE", "DELETE"):
                old = "NULL" if operation == "INSERT" else values("OLD")
                new = "NULL" if operation == "DELETE" else values("NEW")
                record = f"OLD.{key}" if operation == "DELETE" else f"NEW.{key}"
                connection.exec_driver_sql(f"""
                    CREATE TRIGGER audit_{table}_{operation.lower()} AFTER {operation} ON {table}
                    BEGIN
                        INSERT INTO audit_logs (audit_id, table_name, record_id, operation,
                            old_values, new_values, changed_at, changed_by)
                        VALUES (lower(hex(randomblob(16))), '{table}', {record}, '{operation}',
                            {old}, {new}, CURRENT_TIMESTAMP, 'local-database');
                    END
                """)
    for name, query in VIEWS.items():
        connection.exec_driver_sql(f"CREATE VIEW {name} AS {query}")
    if postgres:
        connection.exec_driver_sql("""
            CREATE FUNCTION calculate_transaction_velocity(customer_key varchar, minutes integer)
            RETURNS bigint LANGUAGE sql STABLE AS $$
                SELECT COUNT(*) FROM transactions WHERE customer_id = customer_key
                AND transaction_timestamp >= CURRENT_TIMESTAMP - make_interval(mins => minutes)
                AND transaction_timestamp <= CURRENT_TIMESTAMP
            $$
        """)
        connection.exec_driver_sql("""
            CREATE FUNCTION get_customer_transaction_stats(customer_key varchar)
            RETURNS TABLE(total_transactions bigint, average_transaction_amount numeric,
                transactions_today bigint, suspicious_transactions bigint, maximum_risk_score double precision)
            LANGUAGE sql STABLE AS $$
                SELECT COUNT(t.transaction_id), COALESCE(AVG(t.amount), 0),
                    COUNT(t.transaction_id) FILTER (WHERE t.transaction_timestamp >= date_trunc('day', CURRENT_TIMESTAMP)),
                    COUNT(t.transaction_id) FILTER (WHERE p.classification <> 'NORMAL'),
                    COALESCE(MAX(p.risk_score), 0)
                FROM transactions t LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
                WHERE t.customer_id = customer_key
            $$
        """)


def remove_objects(connection):
    for name in VIEWS:
        connection.exec_driver_sql(f"DROP VIEW IF EXISTS {name}")
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql(
            "DROP TRIGGER IF EXISTS prediction_alert ON fraud_predictions"
        )
        connection.exec_driver_sql("DROP FUNCTION IF EXISTS create_fraud_alert()")
        for table in AUDITED:
            connection.exec_driver_sql(
                f"DROP TRIGGER IF EXISTS audit_{table} ON {table}"
            )
            connection.exec_driver_sql(f"DROP FUNCTION IF EXISTS audit_{table}()")
        connection.exec_driver_sql(
            "DROP FUNCTION IF EXISTS calculate_transaction_velocity(varchar, integer)"
        )
        connection.exec_driver_sql(
            "DROP FUNCTION IF EXISTS get_customer_transaction_stats(varchar)"
        )
    else:
        connection.exec_driver_sql("DROP TRIGGER IF EXISTS prediction_alert")
        for table in AUDITED:
            for operation in ("insert", "update", "delete"):
                connection.exec_driver_sql(
                    f"DROP TRIGGER IF EXISTS audit_{table}_{operation}"
                )
