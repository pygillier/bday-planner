from app.emails import guest_recap_context, send_recap_email
from app.models import RecapEmailTemplate


def test_get_current_creates_default_singleton(app):
    template = RecapEmailTemplate.get_current()
    assert template.id == 1
    assert "{dates}" in template.body

    again = RecapEmailTemplate.get_current()
    assert again.id == template.id
    assert RecapEmailTemplate.query.count() == 1


def test_guest_recap_context_defaults(app, guest):
    with app.test_request_context():
        context = guest_recap_context(guest)
    assert context["prenom"] == "Jeanne"
    assert context["dates"] == "Aucune date sélectionnée"
    assert context["accompagnants"] == "Aucun accompagnant"
    assert context["allergies"] == "Aucune"


def test_guest_recap_context_with_dates_and_plus_ones(app, guest):
    from app.extensions import db
    from app.models import EventOption, PlusOne, utcnow

    option = EventOption(starts_at=utcnow())
    plus_one = PlusOne(guest_id=guest.id, dietary_notes="Sans gluten")
    guest.dietary_notes = "Allergie aux noix"
    guest.event_options.append(option)
    db.session.add_all([option, plus_one])
    db.session.commit()

    with app.test_request_context():
        context = guest_recap_context(guest)
    assert "Sans gluten" in context["accompagnants"]
    assert context["allergies"] == "Allergie aux noix"


def test_send_recap_email_uses_current_app_context(app, guest, monkeypatch):
    sent = {}

    def fake_send(payload):
        sent.update(payload)
        return {"id": "test-message-id"}

    monkeypatch.setattr("app.emails.resend.Emails.send", fake_send)

    with app.test_request_context():
        ok = send_recap_email(guest)

    assert ok is True
    assert sent["to"] == guest.email
    assert "Jeanne" in sent["html"]
    assert f"/rsvp/{guest.token}/details" in sent["html"]


def test_send_recap_email_returns_false_on_failure(app, guest, monkeypatch):
    def fake_send(payload):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.emails.resend.Emails.send", fake_send)

    with app.test_request_context():
        ok = send_recap_email(guest)

    assert ok is False


def test_details_submission_sends_recap_email_once(client, guest, app, monkeypatch):
    from app.models import Guest

    calls = []
    monkeypatch.setattr(
        "app.guest.routes.send_recap_email", lambda g: calls.append(g.id) or True
    )

    client.post(f"/rsvp/{guest.token}/confirmer")
    client.post(f"/rsvp/{guest.token}/details", data={"dietary_notes": "Sans sel"})
    assert calls == [guest.id]

    refreshed = Guest.query.filter_by(token=guest.token).first()
    assert refreshed.recap_sent_at is not None

    client.post(f"/rsvp/{guest.token}/details", data={"dietary_notes": "Sans sel, révisé"})
    assert calls == [guest.id]


def test_details_submission_skips_recap_email_without_address(client, app, monkeypatch):
    from app.extensions import db
    from app.models import Guest

    guest = Guest(first_name="Paul", last_name="Martin", email=None)
    db.session.add(guest)
    db.session.commit()

    calls = []
    monkeypatch.setattr(
        "app.guest.routes.send_recap_email", lambda g: calls.append(g.id) or True
    )

    client.post(f"/rsvp/{guest.token}/confirmer")
    client.post(f"/rsvp/{guest.token}/details", data={"dietary_notes": "Rien à signaler"})
    assert calls == []


def test_recap_email_template_route_requires_login(client):
    response = client.get("/admin/recap-email-template")
    assert response.status_code == 302


def test_recap_email_template_route_saves_changes(admin_client):
    response = admin_client.post(
        "/admin/recap-email-template",
        data={"subject": "Nouvel objet {prenom}", "body": "Nouveau corps {dates}", "action": "save"},
    )
    assert response.status_code == 302
    template = RecapEmailTemplate.get_current()
    assert template.subject == "Nouvel objet {prenom}"
    assert template.body == "Nouveau corps {dates}"
