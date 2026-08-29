from app.extensions import db
from app.models import Guest


def test_send_invitation_email_only(admin_client, monkeypatch):
    calls = {"email": 0, "sms": 0}
    monkeypatch.setattr("app.admin.routes.send_invitation_email", lambda g: calls.__setitem__("email", calls["email"] + 1) or True)
    monkeypatch.setattr("app.admin.routes.send_invitation_sms", lambda g: calls.__setitem__("sms", calls["sms"] + 1) or True)

    guest = Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com")
    db.session.add(guest)
    db.session.commit()

    response = admin_client.post(f"/admin/guests/{guest.id}/send-invitation")
    assert response.status_code == 302
    assert calls == {"email": 1, "sms": 0}


def test_send_invitation_phone_only(admin_client, monkeypatch):
    calls = {"email": 0, "sms": 0}
    monkeypatch.setattr("app.admin.routes.send_invitation_email", lambda g: calls.__setitem__("email", calls["email"] + 1) or True)
    monkeypatch.setattr("app.admin.routes.send_invitation_sms", lambda g: calls.__setitem__("sms", calls["sms"] + 1) or True)

    guest = Guest(first_name="Paul", last_name="Martin", phone="0612345678")
    db.session.add(guest)
    db.session.commit()

    response = admin_client.post(f"/admin/guests/{guest.id}/send-invitation")
    assert response.status_code == 302
    assert calls == {"email": 0, "sms": 1}


def test_send_invitation_both_channels(admin_client, monkeypatch):
    calls = {"email": 0, "sms": 0}
    monkeypatch.setattr("app.admin.routes.send_invitation_email", lambda g: calls.__setitem__("email", calls["email"] + 1) or True)
    monkeypatch.setattr("app.admin.routes.send_invitation_sms", lambda g: calls.__setitem__("sms", calls["sms"] + 1) or True)

    guest = Guest(first_name="Alice", last_name="Durand", email="alice@example.com", phone="0612345678")
    db.session.add(guest)
    db.session.commit()

    response = admin_client.post(f"/admin/guests/{guest.id}/send-invitation")
    assert response.status_code == 302
    assert calls == {"email": 1, "sms": 1}


def test_send_invitation_no_contact_info(admin_client, monkeypatch):
    monkeypatch.setattr("app.admin.routes.send_invitation_email", lambda g: True)
    monkeypatch.setattr("app.admin.routes.send_invitation_sms", lambda g: True)

    guest = Guest(first_name="Sans", last_name="Contact")
    db.session.add(guest)
    db.session.commit()

    response = admin_client.post(f"/admin/guests/{guest.id}/send-invitation", follow_redirects=True)
    assert b"ni adresse e-mail ni num" in response.data


def test_bulk_send_includes_phone_only_guests(admin_client, monkeypatch):
    calls = {"email": 0, "sms": 0}
    monkeypatch.setattr("app.admin.routes.send_invitation_email", lambda g: calls.__setitem__("email", calls["email"] + 1) or True)
    monkeypatch.setattr("app.admin.routes.send_invitation_sms", lambda g: calls.__setitem__("sms", calls["sms"] + 1) or True)

    db.session.add(Guest(first_name="Jeanne", last_name="Dupont", email="jeanne@example.com"))
    db.session.add(Guest(first_name="Paul", last_name="Martin", phone="0612345678"))
    db.session.add(Guest(first_name="Sans", last_name="Contact"))
    db.session.commit()

    response = admin_client.post("/admin/guests/send-invitations")
    assert response.status_code == 302
    assert calls == {"email": 1, "sms": 1}
