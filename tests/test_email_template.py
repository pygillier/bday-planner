from app.emails import (
    render_invitation_body,
    render_invitation_subject,
    send_test_email,
)
from app.models import EmailTemplate


def test_get_current_creates_default_singleton(app):
    template = EmailTemplate.get_current()
    assert template.id == 1
    assert "{prenom}" in template.body

    again = EmailTemplate.get_current()
    assert again.id == template.id
    assert EmailTemplate.query.count() == 1


def test_render_subject_substitutes_variables():
    subject = render_invitation_subject("Coucou {prenom} {nom} !", {"prenom": "Jeanne", "nom": "Dupont"})
    assert subject == "Coucou Jeanne Dupont !"


def test_render_subject_strips_newlines_from_values():
    subject = render_invitation_subject("Bonjour {prenom}", {"prenom": "Evil\r\nBcc: x@y.com"})
    assert "\n" not in subject
    assert "\r" not in subject


def test_render_body_escapes_html_in_template_and_values():
    body = render_invitation_body(
        "<script>alert(1)</script> {prenom}", {"prenom": "<b>Jeanne</b>"}
    )
    assert "<script>" not in str(body)
    assert "&lt;script&gt;" in str(body)
    assert "<b>Jeanne</b>" not in str(body)
    assert "&lt;b&gt;Jeanne&lt;/b&gt;" in str(body)


def test_render_body_paragraphs_and_linebreaks():
    body = render_invitation_body("Ligne 1\nLigne 2\n\nDeuxième paragraphe", {})
    assert str(body) == "<p>Ligne 1<br>Ligne 2</p><p>Deuxième paragraphe</p>"


def test_render_body_empty_returns_empty_markup():
    assert str(render_invitation_body("   \n\n  ", {})) == ""


def test_send_test_email_uses_current_app_context(app, monkeypatch):
    sent = {}

    def fake_send(payload):
        sent.update(payload)
        return {"id": "test-message-id"}

    monkeypatch.setattr("app.emails.resend.Emails.send", fake_send)

    with app.test_request_context():
        ok = send_test_email("someone@example.com", "Objet {prenom}", "Bonjour {prenom}, lien : {lien}")

    assert ok is True
    assert sent["to"] == "someone@example.com"
    assert sent["subject"] == "[Test] Objet Jeanne"
    assert "Bonjour Jeanne" in sent["html"]
    assert "/r/exemple-de-lien" in sent["html"]


def test_send_test_email_returns_false_on_failure(app, monkeypatch):
    def fake_send(payload):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.emails.resend.Emails.send", fake_send)

    with app.test_request_context():
        ok = send_test_email("someone@example.com", "Objet", "Corps")

    assert ok is False


def test_email_template_route_requires_login(client):
    response = client.get("/admin/email-template")
    assert response.status_code == 302


def test_email_template_route_saves_changes(admin_client):
    response = admin_client.post(
        "/admin/email-template",
        data={"subject": "Nouvel objet {prenom}", "body": "Nouveau corps", "action": "save"},
    )
    assert response.status_code == 302
    template = EmailTemplate.get_current()
    assert template.subject == "Nouvel objet {prenom}"
    assert template.body == "Nouveau corps"


def test_email_template_route_saves_signature(admin_client):
    response = admin_client.post(
        "/admin/email-template",
        data={
            "subject": "Objet",
            "body": "Corps",
            "signature": "À bientôt,\nL'organisateur",
            "action": "save",
        },
    )
    assert response.status_code == 302
    template = EmailTemplate.get_current()
    assert template.signature == "À bientôt,\nL'organisateur"


def test_send_test_email_includes_signature(app, monkeypatch):
    sent = {}

    def fake_send(payload):
        sent.update(payload)
        return {"id": "test-message-id"}

    monkeypatch.setattr("app.emails.resend.Emails.send", fake_send)

    with app.test_request_context():
        send_test_email("someone@example.com", "Objet", "Corps", "À bientôt,\nL'organisateur")

    assert "À bientôt" in sent["html"]


def test_email_template_route_test_send_does_not_persist(admin_client, monkeypatch):
    monkeypatch.setattr(
        "app.admin.routes.send_test_email", lambda to, subject, body, signature="": True
    )
    original = EmailTemplate.get_current()
    original_subject = original.subject

    response = admin_client.post(
        "/admin/email-template",
        data={
            "subject": "Draft subject, not saved",
            "body": "Draft body",
            "test_email": "someone@example.com",
            "action": "test",
        },
    )
    assert response.status_code == 200
    assert EmailTemplate.get_current().subject == original_subject
