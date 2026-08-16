import resend
from flask import current_app, render_template, url_for

from app.extensions import db
from app.models import InvitationLog


def send_invitation_email(guest):
    """Send the invitation email for a guest via Resend, logging the outcome.

    Returns True on success, False on failure (never raises -- callers use
    the return value / InvitationLog rows to report a batch summary).
    """
    resend.api_key = current_app.config["RESEND_API_KEY"]
    rsvp_url = url_for("guest.landing", token=guest.token, _external=True)
    html = render_template("emails/invitation.html", guest=guest, rsvp_url=rsvp_url)

    log = InvitationLog(guest_id=guest.id)
    try:
        response = resend.Emails.send(
            {
                "from": current_app.config["RESEND_FROM_EMAIL"],
                "to": guest.email,
                "subject": "Vous êtes invité(e) — 80 ans !",
                "html": html,
            }
        )
        log.resend_message_id = response.get("id") if isinstance(response, dict) else None
        log.status = "sent"
        db.session.add(log)
        guest.invitation_sent_at = db.func.now()
        guest.invitation_sent_count = (guest.invitation_sent_count or 0) + 1
        db.session.commit()
        return True
    except Exception as exc:  # noqa: BLE001 -- Resend SDK can raise several error types
        log.status = "failed"
        log.error_message = str(exc)
        db.session.add(log)
        db.session.commit()
        return False
