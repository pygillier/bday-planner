import resend
from flask import current_app, render_template, url_for
from loguru import logger
from markupsafe import Markup, escape

from app.extensions import db
from app.models import EmailTemplate, InvitationLog


def render_invitation_subject(subject_template, context):
    """Plain-text substitution for the email subject header.

    Newlines are stripped from substituted values to prevent header
    injection via a guest's name (e.g. one imported from a crafted CSV).
    """
    subject = subject_template
    for key, value in context.items():
        safe_value = str(value).replace("\r", " ").replace("\n", " ")
        subject = subject.replace("{" + key + "}", safe_value)
    return subject


def render_invitation_body(body_template, context):
    """HTML-escaped substitution for the email body -- never Jinja/eval, so
    admin-edited content can't achieve template injection. Blank lines
    become paragraph breaks, single newlines become <br>.
    """
    escaped = escape(body_template)
    for key, value in context.items():
        escaped = escaped.replace("{" + key + "}", str(value))

    paragraphs = [para.strip().replace("\n", "<br>") for para in str(escaped).split("\n\n")]
    paragraphs = [para for para in paragraphs if para]
    if not paragraphs:
        return Markup("")
    return Markup("<p>" + "</p><p>".join(paragraphs) + "</p>")


def preview_context():
    """Sample placeholder values used both for the admin edit page's live
    preview and for test-send emails, which aren't tied to a real guest."""
    return {
        "prenom": "Jeanne",
        "nom": "Dupont",
        "lien": url_for("guest.landing", token="exemple-de-lien", _external=True),
    }


def send_test_email(to_email, subject_template, body_template):
    """Send a preview of the invitation email to an arbitrary address, using
    sample placeholder values. Not tied to a guest -- no InvitationLog row,
    no guest state changes. Returns True/False, never raises."""
    resend.api_key = current_app.config["RESEND_API_KEY"]
    context = preview_context()
    subject = render_invitation_subject(subject_template, context)
    body_html = render_invitation_body(body_template, context)
    html = render_template("emails/invitation.html", rsvp_url=context["lien"], body_html=body_html)

    try:
        resend.Emails.send(
            {
                "from": current_app.config["RESEND_FROM_EMAIL"],
                "to": to_email,
                "subject": f"[Test] {subject}",
                "html": html,
            }
        )
        return True
    except Exception:  # noqa: BLE001 -- Resend SDK can raise several error types
        logger.exception("Failed to send test email to {}", to_email)
        return False


def send_invitation_email(guest):
    """Send the invitation email for a guest via Resend, logging the outcome.

    Returns True on success, False on failure (never raises -- callers use
    the return value / InvitationLog rows to report a batch summary).
    """
    resend.api_key = current_app.config["RESEND_API_KEY"]
    rsvp_url = url_for("guest.landing", token=guest.token, _external=True)

    template = EmailTemplate.get_current()
    context = {"prenom": guest.first_name, "nom": guest.last_name, "lien": rsvp_url}
    subject = render_invitation_subject(template.subject, context)
    body_html = render_invitation_body(template.body, context)

    html = render_template("emails/invitation.html", rsvp_url=rsvp_url, body_html=body_html)

    log = InvitationLog(guest_id=guest.id)
    try:
        response = resend.Emails.send(
            {
                "from": current_app.config["RESEND_FROM_EMAIL"],
                "to": guest.email,
                "subject": subject,
                "html": html,
            }
        )
        log.resend_message_id = response.get("id") if isinstance(response, dict) else None
        log.status = "sent"
        db.session.add(log)
        guest.invitation_sent_at = db.func.now()
        guest.invitation_sent_count = (guest.invitation_sent_count or 0) + 1
        db.session.commit()
        logger.info("Invitation email sent to guest {} ({})", guest.id, guest.email)
        return True
    except Exception as exc:  # noqa: BLE001 -- Resend SDK can raise several error types
        logger.exception("Failed to send invitation email to guest {} ({}) - {}", guest.id, guest.email, exc)
        log.status = "failed"
        log.error_message = str(exc)
        db.session.add(log)
        db.session.commit()
        return False
