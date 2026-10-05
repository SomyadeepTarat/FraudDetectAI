"""Threshold, alert/audit triggers, reporting views and PostgreSQL functions."""

from sqlalchemy import text

from alembic import op
from app.db.objects import install_objects, remove_objects
from app.settings import settings

revision = "0002"
down_revision = "0dc7c8edf7f5"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.execute(
        text(
            "INSERT INTO risk_settings (settings_id, fraud_threshold) VALUES (1, :threshold)"
        ),
        {"threshold": settings.fraud_threshold},
    )
    install_objects(connection)


def downgrade():
    remove_objects(op.get_bind())
    op.execute("DELETE FROM risk_settings")
