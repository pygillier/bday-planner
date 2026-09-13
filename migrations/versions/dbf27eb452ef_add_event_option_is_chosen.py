"""add event_option is_chosen

Revision ID: dbf27eb452ef
Revises: 6a96bd12a07d
Create Date: 2026-09-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dbf27eb452ef'
down_revision = '6a96bd12a07d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'event_options',
        sa.Column('is_chosen', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    with op.batch_alter_table('event_options') as batch_op:
        batch_op.alter_column('is_chosen', server_default=None)


def downgrade():
    op.drop_column('event_options', 'is_chosen')
