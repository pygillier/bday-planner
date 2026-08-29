from app.extensions import db
from app.models import Guest, InvitationLog, SmsTemplate
from app.sms import render_sms_body, send_invitation_sms, send_test_sms


class FakeMessages:
    def __init__(self, sid="SMxxxx", raise_exc=None):
        self.sid = sid
        self.raise_exc = raise_exc
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc:
            raise self.raise_exc

        class Message:
            sid = self.sid

        return Message()


class FakeClient:
    def __init__(self, messages):
        self.messages = messages


def _patch_client(monkeypatch, messages):
    monkeypatch.setattr("app.sms.Client", lambda *a, **k: FakeClient(messages))


def test_get_current_creates_default_singleton(app):
    template = SmsTemplate.get_current()
    assert template.id == 1
    assert "{prenom}" in template.body

    again = SmsTemplate.get_current()
    assert again.id == template.id
    assert SmsTemplate.query.count() == 1


def test_render_sms_body_substitutes_without_escaping():
    body = render_sms_body("Bonjour {prenom}, lien : {lien}", {"prenom": "Jeanne", "lien": "http://x/y"})
    assert body == "Bonjour Jeanne, lien : http://x/y"


def test_send_test_sms_uses_current_app_context(app, monkeypatch):
    messages = FakeMessages()
    _patch_client(monkeypatch, messages)

    with app.test_request_context():
        ok = send_test_sms("06 12 34 56 78", "Bonjour {prenom}, lien : {lien}")

    assert ok is True
    assert len(messages.calls) == 1
    assert messages.calls[0]["to"] == "+33612345678"
    assert "Bonjour Jeanne" in messages.calls[0]["body"]


def test_send_test_sms_returns_false_on_invalid_phone(app, monkeypatch):
    messages = FakeMessages()
    _patch_client(monkeypatch, messages)

    with app.test_request_context():
        ok = send_test_sms("not a phone", "Bonjour {prenom}")

    assert ok is False
    assert messages.calls == []


def test_send_invitation_sms_success(app, monkeypatch):
    messages = FakeMessages(sid="SM123")
    _patch_client(monkeypatch, messages)

    guest = Guest(first_name="Jeanne", last_name="Dupont", phone="06 12 34 56 78")
    db.session.add(guest)
    db.session.commit()

    with app.test_request_context():
        ok = send_invitation_sms(guest)

    assert ok is True
    assert guest.invitation_sent_count == 1
    assert guest.invitation_sent_at is not None
    assert messages.calls[0]["to"] == "+33612345678"
    log = InvitationLog.query.filter_by(guest_id=guest.id).first()
    assert log.channel == "sms"
    assert log.status == "sent"
    assert log.provider_message_id == "SM123"


def test_send_invitation_sms_invalid_phone_logs_failure(app, monkeypatch):
    messages = FakeMessages()
    _patch_client(monkeypatch, messages)

    guest = Guest(first_name="Jeanne", last_name="Dupont", phone="invalid")
    db.session.add(guest)
    db.session.commit()

    with app.test_request_context():
        ok = send_invitation_sms(guest)

    assert messages.calls == []

    assert ok is False
    assert guest.invitation_sent_count == 0
    log = InvitationLog.query.filter_by(guest_id=guest.id).first()
    assert log.channel == "sms"
    assert log.status == "failed"


def test_sms_template_route_requires_login(client):
    response = client.get("/admin/sms-template")
    assert response.status_code == 302


def test_sms_template_route_saves_changes(admin_client):
    response = admin_client.post(
        "/admin/sms-template",
        data={"body": "Nouveau message {prenom}", "action": "save"},
    )
    assert response.status_code == 302
    template = SmsTemplate.get_current()
    assert template.body == "Nouveau message {prenom}"


def test_sms_template_route_test_send_does_not_persist(admin_client, monkeypatch):
    monkeypatch.setattr(
        "app.admin.routes.send_test_sms", lambda to, body, signature="": True
    )
    original = SmsTemplate.get_current()
    original_body = original.body

    response = admin_client.post(
        "/admin/sms-template",
        data={
            "body": "Draft body, not saved",
            "test_phone": "0612345678",
            "action": "test",
        },
    )
    assert response.status_code == 200
    assert SmsTemplate.get_current().body == original_body
