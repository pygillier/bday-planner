from flask import current_app, url_for
from loguru import logger
from twilio.base.exceptions import TwilioException
from twilio.rest import Client

from app.extensions import db
from app.markdown_utils import render_follow_up_sms_text
from app.models import FollowUpLog, InvitationLog, SmsTemplate, chosen_date_display
from app.phone import to_e164_fr


def render_sms_body(body_template, context):
    """Plain-text substitution for the SMS body -- SMS is not rendered in a
    browser, so no HTML-escaping is needed (unlike render_invitation_body)."""
    text = body_template
    for key, value in context.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def sms_preview_context():
    """Sample placeholder values used for the admin edit page's live
    preview and for test-send SMS, which aren't tied to a real guest."""
    return {
        "prenom": "Jeanne",
        "nom": "Dupont",
        "lien": url_for("guest.landing", token="exemple", _external=True),
    }


def follow_up_sms_preview_context():
    """Sample placeholder values for the follow-up compose page's live
    preview and test-send SMS. Includes the organizer-chosen date, unlike
    sms_preview_context."""
    return {
        "prenom": "Jeanne",
        "nom": "Dupont",
        "date": chosen_date_display(),
        "lien": url_for("guest.landing", token="exemple", _external=True),
    }


def _twilio_client():
    api_key_sid = current_app.config.get("TWILIO_API_KEY_SID")
    api_key_secret = current_app.config.get("TWILIO_API_KEY_SECRET")
    if api_key_sid and api_key_secret:
        username, password = api_key_sid, api_key_secret
    else:
        username, password = current_app.config["TWILIO_ACCOUNT_SID"], current_app.config["TWILIO_AUTH_TOKEN"]

    return Client(
        username,
        password,
        account_sid=current_app.config["TWILIO_ACCOUNT_SID"],
        region=current_app.config.get("TWILIO_REGION"),
        edge=current_app.config.get("TWILIO_EDGE"),
    )


def send_test_sms(to_phone, body_template, signature_template=""):
    """Send a preview of the invitation SMS to an arbitrary phone number,
    using sample placeholder values. Not tied to a guest -- no InvitationLog
    row, no guest state changes. Returns True/False, never raises."""
    e164 = to_e164_fr(to_phone)
    if e164 is None:
        logger.warning("Refusing to send test SMS to invalid phone number {}", to_phone)
        return False

    context = sms_preview_context()
    body = render_sms_body(body_template, context)
    signature = render_sms_body(signature_template, context)
    text = f"[Test] {body}" + (f"\n{signature}" if signature else "")

    try:
        _twilio_client().messages.create(to=e164, from_=current_app.config["TWILIO_FROM_NUMBER"], body=text)
        logger.info("Test SMS sent to {}", to_phone)
        return True
    except TwilioException:
        logger.exception("Failed to send test SMS to {}", to_phone)
        return False


def send_invitation_sms(guest):
    """Send the invitation SMS for a guest via Twilio, logging the outcome.

    Returns True on success, False on failure (never raises -- callers use
    the return value / InvitationLog rows to report a batch summary).
    """
    log = InvitationLog(guest_id=guest.id, channel="sms")

    e164 = to_e164_fr(guest.phone)
    if e164 is None:
        logger.warning("Cannot send invitation SMS to guest {} - invalid phone {}", guest.id, guest.phone)
        log.status = "failed"
        log.error_message = "Numéro de téléphone invalide."
        db.session.add(log)
        db.session.commit()
        return False

    rsvp_url = url_for("guest.landing", token=guest.token, _external=True)
    template = SmsTemplate.get_current()
    context = {"prenom": guest.first_name, "nom": guest.last_name, "lien": rsvp_url}
    body = render_sms_body(template.body, context)
    signature = render_sms_body(template.signature, context)
    text = body + (f"\n{signature}" if signature else "")

    try:
        message = _twilio_client().messages.create(
            to=e164, from_=current_app.config["TWILIO_FROM_NUMBER"], body=text
        )
        log.provider_message_id = message.sid
        log.status = "sent"
        db.session.add(log)
        guest.invitation_sent_at = db.func.now()
        guest.invitation_sent_count = (guest.invitation_sent_count or 0) + 1
        db.session.commit()
        logger.info("Invitation SMS sent to guest {} ({})", guest.id, e164)
        return True
    except TwilioException as exc:
        logger.exception("Failed to send invitation SMS to guest {} ({}) - {}", guest.id, e164, exc)
        log.status = "failed"
        log.error_message = str(exc)
        db.session.add(log)
        db.session.commit()
        return False


def send_test_follow_up_sms(to_phone, body_template):
    """Send a preview of an ad-hoc follow-up SMS to an arbitrary phone
    number, using sample placeholder values. Not tied to a guest -- no
    FollowUpLog row. Returns True/False, never raises."""
    e164 = to_e164_fr(to_phone)
    if e164 is None:
        logger.warning("Refusing to send test follow-up SMS to invalid phone number {}", to_phone)
        return False

    context = follow_up_sms_preview_context()
    text = f"[Test] {render_follow_up_sms_text(body_template, context)}"

    try:
        _twilio_client().messages.create(to=e164, from_=current_app.config["TWILIO_FROM_NUMBER"], body=text)
        logger.info("Test follow-up SMS sent to {}", to_phone)
        return True
    except TwilioException:
        logger.exception("Failed to send test follow-up SMS to {}", to_phone)
        return False


def send_follow_up_sms(guest, body_template):
    """Send an ad-hoc follow-up SMS to a guest via Twilio, logging the
    outcome to FollowUpLog. Unlike send_invitation_sms, this never touches
    guest.invitation_sent_at/invitation_sent_count. Returns True/False,
    never raises."""
    log = FollowUpLog(guest_id=guest.id, channel="sms", body="")

    e164 = to_e164_fr(guest.phone)
    if e164 is None:
        logger.warning("Cannot send follow-up SMS to guest {} - invalid phone {}", guest.id, guest.phone)
        log.status = "failed"
        log.error_message = "Numéro de téléphone invalide."
        db.session.add(log)
        db.session.commit()
        return False

    context = {
        "prenom": guest.first_name,
        "nom": guest.last_name,
        "date": chosen_date_display(),
        "lien": url_for("guest.landing", token=guest.token, _external=True),
    }
    text = render_follow_up_sms_text(body_template, context)
    log.body = text

    try:
        message = _twilio_client().messages.create(to=e164, from_=current_app.config["TWILIO_FROM_NUMBER"], body=text)
        log.provider_message_id = message.sid
        log.status = "sent"
        db.session.add(log)
        db.session.commit()
        logger.info("Follow-up SMS sent to guest {} ({})", guest.id, e164)
        return True
    except TwilioException as exc:
        logger.exception("Failed to send follow-up SMS to guest {} ({}) - {}", guest.id, e164, exc)
        log.status = "failed"
        log.error_message = str(exc)
        db.session.add(log)
        db.session.commit()
        return False
