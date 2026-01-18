"""add password migration flag

Revision ID: b4fa2afffb04
Revises:
Create Date: 2026-01-18 14:37:24.307031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4fa2afffb04'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password_migration_required column to users table"""
    op.add_column('users', sa.Column('password_migration_required', sa.Boolean(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Remove password_migration_required column from users table"""
    op.drop_column('users', 'password_migration_required')
