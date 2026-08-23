import secrets
from datetime import UTC, datetime

from app.extensions import db


def utcnow():
    return datetime.now(UTC)


guest_event_options = db.Table(
    "guest_event_options",
    db.Column("guest_id", db.Integer, db.ForeignKey("guests.id"), primary_key=True),
    db.Column("event_option_id", db.Integer, db.ForeignKey("event_options.id"), primary_key=True),
)


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
    recap_sent_at = db.Column(db.DateTime, nullable=True)

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
    event_logs = db.relationship(
        "GuestEventLog", backref="guest", cascade="all, delete-orphan", order_by="GuestEventLog.created_at.desc()"
    )
    event_options = db.relationship(
        "EventOption",
        secondary=guest_event_options,
        backref="guests",
        order_by="EventOption.starts_at",
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


GUEST_EVENT_LABELS = {
    "confirmed": "A confirmé sa présence",
    "declined": "A décliné l'invitation",
    "updated": "A mis à jour ses informations",
    "reset": "Réponse réinitialisée par l'organisateur",
}


class GuestEventLog(db.Model):
    """Audit trail of guest-initiated actions (RSVP + detail updates), for the admin."""

    __tablename__ = "guest_event_logs"

    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey("guests.id"), nullable=False)
    event_type = db.Column(db.String(30), nullable=False)
    detail = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    @property
    def label(self):
        return GUEST_EVENT_LABELS.get(self.event_type, self.event_type)


FR_WEEKDAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
FR_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def format_date_fr(dt):
    """French date/time formatting without relying on server locale."""
    time_part = dt.strftime("%Hh%M") if dt.minute else dt.strftime("%Hh")
    return f"{FR_WEEKDAYS[dt.weekday()]} {dt.day} {FR_MONTHS[dt.month - 1]} {dt.year} à {time_part}"


class EventOption(db.Model):
    """A candidate date/time for the party. The admin offers whichever
    options are configured here; guests may select several of them --
    whichever they'd be available for -- and the organizer picks the
    final date from the aggregated answers."""

    __tablename__ = "event_options"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(255), nullable=True)
    starts_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    @property
    def display_text(self):
        formatted = format_date_fr(self.starts_at)
        return f"{self.label} — {formatted}" if self.label else formatted


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
    signature = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    @classmethod
    def get_current(cls):
        template = db.session.get(cls, 1)
        if template is None:
            template = cls(id=1, subject=DEFAULT_EMAIL_SUBJECT, body=DEFAULT_EMAIL_BODY)
            db.session.add(template)
            db.session.commit()
        return template


RECAP_EMAIL_VARIABLES = {
    "prenom": "Prénom de l'invité·e",
    "nom": "Nom de l'invité·e",
    "dates": "Dates choisies par l'invité·e",
    "accompagnants": "Détail des accompagnant·e·s",
    "allergies": "Allergies / notes de l'invité·e",
    "lien": "Lien personnel pour modifier sa réponse",
}

DEFAULT_RECAP_EMAIL_SUBJECT = "Récapitulatif de votre réponse — 80 ans !"

DEFAULT_RECAP_EMAIL_BODY = (
    "Bonjour {prenom},\n\n"
    "Merci pour votre réponse ! Voici un récapitulatif :\n\n"
    "Dates choisies : {dates}\n"
    "Accompagnant·e·s : {accompagnants}\n"
    "Allergies / notes : {allergies}\n\n"
    "Conservez cet e-mail : vous pourrez revenir à tout moment sur votre réponse "
    "en cliquant sur le bouton ci-dessous."
)


class RecapEmailTemplate(db.Model):
    """Single editable template for the recap e-mail sent to a guest the
    first time they complete the details form (dates, plus-ones, dietary
    notes). Same substitution model as EmailTemplate -- plain string
    .replace() + escaping, never Jinja -- for the same reason (see
    EmailTemplate's docstring)."""

    __tablename__ = "recap_email_templates"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False, default=DEFAULT_RECAP_EMAIL_SUBJECT)
    body = db.Column(db.Text, nullable=False, default=DEFAULT_RECAP_EMAIL_BODY)
    signature = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    @classmethod
    def get_current(cls):
        template = db.session.get(cls, 1)
        if template is None:
            template = cls(id=1, subject=DEFAULT_RECAP_EMAIL_SUBJECT, body=DEFAULT_RECAP_EMAIL_BODY)
            db.session.add(template)
            db.session.commit()
        return template
