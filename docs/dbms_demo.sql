-- FraudDetectAI PostgreSQL practical evaluation.
-- All mutations below are enclosed in a rollback so existing rows remain unchanged.
-- Run against the migrated, seeded local demo database, e.g.:
-- docker compose exec -T postgres psql -U frauddetect -d frauddetect < docs/dbms_demo.sql

-- SELECT and filtering.
SELECT transaction_id, customer_id, amount, status
FROM transactions WHERE amount >= 4500 ORDER BY transaction_timestamp DESC LIMIT 10;

-- INNER JOIN and LEFT JOIN: show customers, accounts, predictions and optional alerts.
SELECT c.name, a.account_id, t.transaction_id, t.amount,
       p.fraud_probability, p.risk_score, f.alert_status
FROM customers c
INNER JOIN accounts a ON a.customer_id = c.customer_id
INNER JOIN transactions t ON t.account_id = a.account_id
INNER JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
LEFT JOIN fraud_alerts f ON f.prediction_id = p.prediction_id
ORDER BY p.risk_score DESC LIMIT 20;

-- COUNT, AVG, MAX, MIN, SUM, GROUP BY and HAVING.
SELECT c.customer_id, c.name, COUNT(t.transaction_id) AS transfers,
       AVG(t.amount) AS average_amount, MAX(t.amount) AS largest_amount,
       MIN(t.amount) AS smallest_amount, SUM(t.amount) AS total_amount
FROM customers c JOIN transactions t ON t.customer_id = c.customer_id
GROUP BY c.customer_id, c.name HAVING COUNT(t.transaction_id) > 2;

-- Customers with more than two suspicious transactions.
SELECT c.customer_id, c.name, COUNT(*) AS suspicious_count
FROM customers c JOIN transactions t ON t.customer_id = c.customer_id
JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
WHERE p.classification <> 'NORMAL'
GROUP BY c.customer_id, c.name HAVING COUNT(*) > 2
ORDER BY suspicious_count DESC;

-- Correlated nested query: exceeds 3x *prior* customer average (exclude current/future rows).
SELECT t.transaction_id, t.customer_id, t.amount
FROM transactions t
WHERE t.amount > 3 * (
    SELECT AVG(h.amount) FROM transactions h
    WHERE h.customer_id = t.customer_id
      AND h.transaction_timestamp < t.transaction_timestamp
) ORDER BY t.amount DESC LIMIT 20;

-- Database views.
SELECT * FROM suspicious_transactions_view ORDER BY risk_score DESC LIMIT 20;
SELECT * FROM customer_risk_summary ORDER BY maximum_risk_score DESC;

-- Real stored SQL functions.
SELECT * FROM get_customer_transaction_stats('C001');
SELECT calculate_transaction_velocity('C001', 10);

-- Inspect installed indexes and triggers.
SELECT tablename, indexname, indexdef FROM pg_indexes
WHERE schemaname = current_schema() ORDER BY tablename, indexname;
SELECT trigger_name, event_object_table, event_manipulation
FROM information_schema.triggers WHERE trigger_schema = current_schema();

-- Measured plan: no forced index/no invented performance improvements.
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) FROM transactions
WHERE customer_id = 'C001'
  AND transaction_timestamp >= CURRENT_TIMESTAMP - INTERVAL '10 minutes';

-- INSERT, UPDATE, DELETE, constraints, row locking and ROLLBACK.
BEGIN;
INSERT INTO customers (customer_id, name, email, status, created_at)
VALUES ('SQL-DEMO-C', 'Disposable SQL demo', 'sql-demo@demo.example', 'ACTIVE', CURRENT_TIMESTAMP);
INSERT INTO accounts (account_id, customer_id, account_type, balance, currency, status, created_at)
VALUES ('SQL-DEMO-A', 'SQL-DEMO-C', 'SAVINGS', 10000, 'INR', 'ACTIVE', CURRENT_TIMESTAMP),
       ('SQL-DEMO-B', 'SQL-DEMO-C', 'SAVINGS', 0, 'INR', 'ACTIVE', CURRENT_TIMESTAMP);
SELECT * FROM accounts WHERE account_id IN ('SQL-DEMO-A', 'SQL-DEMO-B') ORDER BY account_id FOR UPDATE;
UPDATE accounts SET balance = balance - 1000 WHERE account_id = 'SQL-DEMO-A';
UPDATE accounts SET balance = balance + 1000 WHERE account_id = 'SQL-DEMO-B';
UPDATE customers SET status = 'UNDER_REVIEW' WHERE customer_id = 'SQL-DEMO-C';
SELECT table_name, operation, old_values, new_values FROM audit_logs
WHERE record_id IN ('SQL-DEMO-C', 'SQL-DEMO-A', 'SQL-DEMO-B');
DELETE FROM accounts WHERE account_id IN ('SQL-DEMO-A', 'SQL-DEMO-B');
DELETE FROM customers WHERE customer_id = 'SQL-DEMO-C';
ROLLBACK;
-- Atomic rollback removes even the INSERT/UPDATE/DELETE audit events above.
SELECT * FROM customers WHERE customer_id = 'SQL-DEMO-C';

-- Threshold is persisted and shared by classification and trigger; changing it is transactional.
BEGIN;
UPDATE risk_settings SET fraud_threshold = 0.85 WHERE settings_id = 1;
SELECT * FROM risk_settings;
ROLLBACK;

-- For COMMIT, model integration, and rollback after an essential failure, use the
-- transaction API and scripts/demo_rollback.py instead of hand-writing model outputs.
-- For simultaneous independent connections and FOR UPDATE protection use
-- scripts/demo_concurrency.py; it asserts exactly one debit/prediction commits.
