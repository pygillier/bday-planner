import secrets
from datetime import UTC, datetime

from app.extensions import db


def utcnow():
    return datetime.now(UTC)


class Guest(db.Model):
    __tablename__ = "guests"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(
        db.String(43), unique=True, nullable=False, index=True,
        default=lambda: secrets.token_urlsafe(32),
    )
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)

    rsvp_status = db.Column(db.String(20), nullable=False, default="pending")
    rsvp_updated_at = db.Column(db.DateTime, nullable=True)

    dietary_notes = db.Column(db.Text, nullable=True)

    invitation_sent_at = db.Column(db.DateTime, nullable=True)
    invitation_sent_count = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    plus_ones = db.relationship(
        "PlusOne", backref="guest", cascade="all, delete-orphan", order_by="PlusOne.id"
    )
    invitation_logs = db.relationship(
        "InvitationLog", backref="guest", cascade="all, delete-orphan", order_by="InvitationLog.sent_at.desc()"
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def headcount(self):
        if self.rsvp_status != "confirmed":
            return 0
        return 1 + len(self.plus_ones)


class PlusOne(db.Model):
    """An accompanying guest. No name is collected -- rows are identified by
    order only ('Accompagnant 1', 'Accompagnant 2', ...)."""

    __tablename__ = "plus_ones"

    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey("guests.id"), nullable=False)
    dietary_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class InvitationLog(db.Model):
    """Audit trail of Resend sends, for troubleshooting delivery."""

    __tablename__ = "invitation_logs"

    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey("guests.id"), nullable=False)
    sent_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    resend_message_id = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="sent")
    error_message = db.Column(db.Text, nullable=True)
