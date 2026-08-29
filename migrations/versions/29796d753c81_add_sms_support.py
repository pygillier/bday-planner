"""add sms support

Revision ID: 29796d753c81
Revises: 53a453d570b9
Create Date: 2026-08-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '29796d753c81'
down_revision = '53a453d570b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sms_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    with op.batch_alter_table('invitation_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('channel', sa.String(length=10), nullable=False, server_default='email'))
        batch_op.alter_column('resend_message_id', new_column_name='provider_message_id')

    with op.batch_alter_table('invitation_logs', schema=None) as batch_op:
        batch_op.alter_column('channel', server_default=None)


def downgrade():
    with op.batch_alter_table('invitation_logs', schema=None) as batch_op:
        batch_op.alter_column('provider_message_id', new_column_name='resend_message_id')
        batch_op.drop_column('channel')

    op.drop_table('sms_templates')
