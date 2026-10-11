"""limiares de RX óptico em app_settings

Revision ID: c4e8a1b27d09
Revises: 730cf63cba2a
Create Date: 2026-10-11 03:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e8a1b27d09"
down_revision: Union[str, None] = "730cf63cba2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("optical_rx_no_signal_dbm", sa.Float(), nullable=False, server_default="-30"),
    )
    op.add_column(
        "app_settings",
        sa.Column("optical_rx_critical_dbm", sa.Float(), nullable=False, server_default="-27"),
    )
    op.add_column(
        "app_settings",
        sa.Column("optical_rx_warning_dbm", sa.Float(), nullable=False, server_default="-24"),
    )
    op.add_column(
        "app_settings",
        sa.Column("optical_rx_overload_dbm", sa.Float(), nullable=False, server_default="-8"),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "optical_rx_overload_dbm")
    op.drop_column("app_settings", "optical_rx_warning_dbm")
    op.drop_column("app_settings", "optical_rx_critical_dbm")
    op.drop_column("app_settings", "optical_rx_no_signal_dbm")
