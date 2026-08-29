"""shorten guest tokens for sms-friendly links

Revision ID: f33b74e192b3
Revises: 29796d753c81
Create Date: 2026-08-29 00:00:01.000000

Regenerates every guest's token as a short (8-char) secrets.token_urlsafe(6)
value instead of the original 43-char token_urlsafe(32), so the personal
RSVP link fits comfortably in an SMS. Any previously sent long links stop
working -- acceptable since this app has no token-expiry story and
regenerate-link is already the documented way to reissue a link.

downgrade() cannot recover the original long tokens (not stored anywhere);
it regenerates fresh 43-char tokens instead, which is the closest
equivalent to the pre-migration state.
"""
import secrets

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f33b74e192b3'
down_revision = '29796d753c81'
branch_labels = None
depends_on = None


guests = sa.table('guests', sa.column('id', sa.Integer), sa.column('token', sa.String))


def _regenerate_tokens(connection, token_bytes):
    ids = [row.id for row in connection.execute(sa.select(guests.c.id))]
    seen = set()
    for guest_id in ids:
        token = secrets.token_urlsafe(token_bytes)
        while token in seen:
            token = secrets.token_urlsafe(token_bytes)
        seen.add(token)
        connection.execute(guests.update().where(guests.c.id == guest_id).values(token=token))


def upgrade():
    _regenerate_tokens(op.get_bind(), 6)


def downgrade():
    _regenerate_tokens(op.get_bind(), 32)
