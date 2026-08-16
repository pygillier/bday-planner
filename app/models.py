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


EMAIL_VARIABLES = {
    "prenom": "Prénom de l'invité·e",
    "nom": "Nom de l'invité·e",
    "lien": "Lien personnel de confirmation",
}

DEFAULT_EMAIL_SUBJECT = "Vous êtes invité(e) — 80 ans !"

DEFAULT_EMAIL_BODY = (
    "Bonjour {prenom},\n\n"
    "Vous êtes invité·e à fêter les 80 ans en famille.\n\n"
    "Merci de confirmer votre présence en cliquant sur le bouton ci-dessous."
)


class EmailTemplate(db.Model):
    """Single editable template for the guest invitation email.

    The body is plain text with named placeholders (see EMAIL_VARIABLES),
    substituted with HTML-escaping at send time -- never rendered through
    Jinja, so an admin editing this content can't achieve template
    injection even though any successful Pocket ID login can reach this
    form (see app/admin/routes.py's auth model)."""

    __tablename__ = "email_templates"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False, default=DEFAULT_EMAIL_SUBJECT)
    body = db.Column(db.Text, nullable=False, default=DEFAULT_EMAIL_BODY)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    @classmethod
    def get_current(cls):
        template = db.session.get(cls, 1)
        if template is None:
            template = cls(id=1, subject=DEFAULT_EMAIL_SUBJECT, body=DEFAULT_EMAIL_BODY)
            db.session.add(template)
            db.session.commit()
        return template
