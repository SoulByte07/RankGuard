"""add users, transactions, user_snapshots, rankings

Revision ID: f3cae054f440
Revises: 
Create Date: 2026-06-24 11:21:15.145372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = 'f3cae054f440'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table('transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('idempotency_key', sa.String(255), nullable=False, unique=True),
        sa.Column('type', sa.Enum('earn', 'spend', 'bonus', name='transaction_type'), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('extra_data', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table('user_snapshots',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('total_earned', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('total_spent', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('net_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('transaction_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('bonus_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table('rankings',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('score', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('rankings')
    op.drop_table('user_snapshots')
    op.drop_table('transactions')
    op.execute('DROP TYPE IF EXISTS transaction_type')
    op.drop_table('users')
