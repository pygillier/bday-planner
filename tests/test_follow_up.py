from datetime import datetime

from app.extensions import db
from app.models import EventOption, FollowUpLog, Guest


def test_follow_up_route_requires_login(client):
    response = client.get("/admin/follow-up")
    assert response.status_code == 302


def test_follow_up_lists_only_matching_status(admin_client):
    db.session.add(Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com", rsvp_status="pending"))
    db.session.add(Guest(first_name="Paul", last_name="Martin", email="paul@example.com", rsvp_status="confirmed"))
    db.session.commit()

    response = admin_client.get("/admin/follow-up?status_filter=confirmed")
    assert response.status_code == 200
    assert b"Paul Martin" in response.data
    assert b"Jeanne Dupont" not in response.data


def test_follow_up_send_respects_checkbox_exclusion(admin_client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.admin.routes.send_follow_up_email",
        lambda guest, subject, body: calls.append(guest.id) or True,
    )

    included = Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com", rsvp_status="confirmed")
    excluded = Guest(first_name="Paul", last_name="Martin", email="paul@example.com", rsvp_status="confirmed")
    db.session.add(included)
    db.session.add(excluded)
    db.session.commit()

    response = admin_client.post(
        "/admin/follow-up",
        data={
            "action": "send",
            "status_filter": "confirmed",
            "channel_email": "y",
            "subject": "Un petit mot",
            "body": "Bonjour {prenom}",
            "guest_ids": str(included.id),
        },
    )
    assert response.status_code == 302
    assert calls == [included.id]


def test_follow_up_send_both_channels_creates_two_logs(admin_client, monkeypatch):
    monkeypatch.setattr("app.admin.routes.send_follow_up_email", lambda guest, subject, body: True)
    monkeypatch.setattr("app.admin.routes.send_follow_up_sms", lambda guest, body: True)

    guest = Guest(
        first_name="Alice",
        last_name="Durand",
        email="alice@example.com",
        phone="0612345678",
        rsvp_status="pending",
    )
    db.session.add(guest)
    db.session.commit()

    response = admin_client.post(
        "/admin/follow-up",
        data={
            "action": "send",
            "status_filter": "pending",
            "channel_email": "y",
            "channel_sms": "y",
            "subject": "Un petit mot",
            "body": "Bonjour {prenom}",
            "guest_ids": str(guest.id),
        },
    )
    assert response.status_code == 302


def test_follow_up_creates_failed_log_on_provider_error(admin_client, monkeypatch):
    def fake_send(guest, subject, body):
        log = FollowUpLog(guest_id=guest.id, channel="email", subject=subject, body="", status="failed", error_message="boom")
        db.session.add(log)
        db.session.commit()
        return False

    monkeypatch.setattr("app.admin.routes.send_follow_up_email", fake_send)

    guest = Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com", rsvp_status="pending")
    db.session.add(guest)
    db.session.commit()

    response = admin_client.post(
        "/admin/follow-up",
        data={
            "action": "send",
            "status_filter": "pending",
            "channel_email": "y",
            "subject": "Un petit mot",
            "body": "Bonjour {prenom}",
            "guest_ids": str(guest.id),
        },
    )
    assert response.status_code == 302
    log = FollowUpLog.query.filter_by(guest_id=guest.id).first()
    assert log.status == "failed"
    assert log.error_message == "boom"


def test_follow_up_test_send_does_not_create_log_or_touch_guests(admin_client, monkeypatch):
    monkeypatch.setattr("app.admin.routes.send_test_follow_up_email", lambda to, subject, body: True)

    guest = Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com", rsvp_status="pending")
    db.session.add(guest)
    db.session.commit()

    response = admin_client.post(
        "/admin/follow-up",
        data={
            "action": "test",
            "status_filter": "pending",
            "channel_email": "y",
            "subject": "Un petit mot",
            "body": "Bonjour {prenom}",
            "test_email": "test@example.com",
        },
    )
    assert response.status_code == 200
    assert FollowUpLog.query.count() == 0
    assert Guest.query.get(guest.id).invitation_sent_at is None


def test_follow_up_appears_in_journal(admin_client, monkeypatch):
    monkeypatch.setattr("app.emails.resend.Emails.send", lambda payload: {"id": "test-message-id"})

    guest = Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com", rsvp_status="pending")
    db.session.add(guest)
    db.session.commit()

    admin_client.post(
        "/admin/follow-up",
        data={
            "action": "send",
            "status_filter": "pending",
            "channel_email": "y",
            "subject": "Nouvelles concernant la date",
            "body": "Bonjour {prenom}",
            "guest_ids": str(guest.id),
        },
    )

    response = admin_client.get("/admin/journal")
    assert response.status_code == 200
    assert "Nouvelles concernant la date".encode() in response.data


def test_follow_up_date_placeholder_uses_chosen_option(admin_client, monkeypatch):
    monkeypatch.setattr("app.emails.resend.Emails.send", lambda payload: {"id": "test-message-id"})

    option = EventOption(label="Samedi", starts_at=datetime(2026, 9, 12, 15, 0), is_chosen=True)
    db.session.add(option)
    guest = Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com", rsvp_status="pending")
    db.session.add(guest)
    db.session.commit()

    admin_client.post(
        "/admin/follow-up",
        data={
            "action": "send",
            "status_filter": "pending",
            "channel_email": "y",
            "subject": "Nouvelles concernant la date",
            "body": "Rendez-vous le {date}",
            "guest_ids": str(guest.id),
        },
    )

    log = FollowUpLog.query.filter_by(guest_id=guest.id).first()
    assert option.display_text in log.body


def test_follow_up_date_placeholder_falls_back_when_no_option_chosen(admin_client, monkeypatch):
    monkeypatch.setattr("app.emails.resend.Emails.send", lambda payload: {"id": "test-message-id"})

    guest = Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com", rsvp_status="pending")
    db.session.add(guest)
    db.session.commit()

    admin_client.post(
        "/admin/follow-up",
        data={
            "action": "send",
            "status_filter": "pending",
            "channel_email": "y",
            "subject": "Nouvelles concernant la date",
            "body": "Rendez-vous le {date}",
            "guest_ids": str(guest.id),
        },
    )

    log = FollowUpLog.query.filter_by(guest_id=guest.id).first()
    assert "Date à confirmer" in log.body
