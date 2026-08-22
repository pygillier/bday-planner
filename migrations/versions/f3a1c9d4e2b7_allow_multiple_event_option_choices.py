"""allow multiple event option choices per guest

Revision ID: f3a1c9d4e2b7
Revises: 8afc172381af
Create Date: 2026-08-22 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a1c9d4e2b7'
down_revision = '8afc172381af'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'guest_event_options',
        sa.Column('guest_id', sa.Integer(), nullable=False),
        sa.Column('event_option_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['event_option_id'], ['event_options.id']),
        sa.ForeignKeyConstraint(['guest_id'], ['guests.id']),
        sa.PrimaryKeyConstraint('guest_id', 'event_option_id'),
    )

    guests = sa.table(
        'guests',
        sa.column('id', sa.Integer),
        sa.column('event_option_id', sa.Integer),
    )
    guest_event_options = sa.table(
        'guest_event_options',
        sa.column('guest_id', sa.Integer),
        sa.column('event_option_id', sa.Integer),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(guests.c.id, guests.c.event_option_id).where(
            guests.c.event_option_id.isnot(None)
        )
    ).fetchall()
    if rows:
        connection.execute(
            guest_event_options.insert(),
            [{"guest_id": row.id, "event_option_id": row.event_option_id} for row in rows],
        )

    with op.batch_alter_table('guests', schema=None) as batch_op:
        batch_op.drop_constraint('guests_event_option_id_fkey', type_='foreignkey')
        batch_op.drop_column('event_option_id')


def downgrade():
    with op.batch_alter_table('guests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('event_option_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'event_options', ['event_option_id'], ['id'])

    guests = sa.table(
        'guests',
        sa.column('id', sa.Integer),
        sa.column('event_option_id', sa.Integer),
    )
    guest_event_options = sa.table(
        'guest_event_options',
        sa.column('guest_id', sa.Integer),
        sa.column('event_option_id', sa.Integer),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(guest_event_options.c.guest_id, guest_event_options.c.event_option_id)
    ).fetchall()
    for row in rows:
        connection.execute(
            guests.update()
            .where(guests.c.id == row.guest_id)
            .values(event_option_id=row.event_option_id)
        )

    op.drop_table('guest_event_options')
