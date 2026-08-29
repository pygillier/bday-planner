def test_landing_shows_greeting(client, guest):
    response = client.get(f"/r/{guest.token}", follow_redirects=True)
    assert response.status_code == 200
    assert "Jeanne".encode() in response.data


def test_invalid_token_returns_404(client):
    response = client.get("/r/does-not-exist")
    assert response.status_code == 404


def test_confirm_then_decline(client, guest):
    client.post(f"/r/{guest.token}/confirmer")
    response = client.get(f"/r/{guest.token}", follow_redirects=True)
    assert "confirm".encode() in response.data.lower()

    client.post(f"/r/{guest.token}/decliner")
    response = client.get(f"/r/{guest.token}")
    assert "d\xe9clin".encode("utf-8") in response.data.lower() or b"pas pouvoir venir" in response.data


def test_add_and_remove_plus_one(client, guest, app):
    from app.models import Guest

    client.post(f"/r/{guest.token}/confirmer")
    client.post(f"/r/{guest.token}/details/plus-one/add")

    refreshed = Guest.query.filter_by(token=guest.token).first()
    assert len(refreshed.plus_ones) == 1

    plus_one_id = refreshed.plus_ones[0].id
    client.post(f"/r/{guest.token}/details/plus-one/{plus_one_id}/remove")

    refreshed = Guest.query.filter_by(token=guest.token).first()
    assert len(refreshed.plus_ones) == 0


def test_details_accessible_before_confirmation(client, guest):
    response = client.get(f"/r/{guest.token}/details")
    assert response.status_code == 200


def test_details_redirects_to_landing_when_declined(client, guest):
    client.post(f"/r/{guest.token}/decliner")
    response = client.get(f"/r/{guest.token}/details")
    assert response.status_code == 302


def test_admin_reset_answer_clears_guest_state(admin_client, guest, app):
    from app.extensions import db
    from app.models import EventOption, Guest, PlusOne, utcnow

    option = EventOption(starts_at=utcnow())
    db.session.add(option)
    db.session.commit()

    admin_client.post(f"/r/{guest.token}/confirmer")
    admin_client.post(
        f"/r/{guest.token}/details",
        data={"dietary_notes": "Sans sel", "event_option_ids": [option.id]},
    )
    db.session.add(PlusOne(guest_id=guest.id, dietary_notes="Sans gluten"))
    db.session.commit()

    response = admin_client.post(f"/admin/guests/{guest.id}/reset-answer")
    assert response.status_code == 302

    refreshed = Guest.query.get(guest.id)
    assert refreshed.rsvp_status == "pending"
    assert refreshed.rsvp_updated_at is None
    assert refreshed.dietary_notes is None
    assert refreshed.event_options == []
    assert refreshed.plus_ones == []
    assert refreshed.recap_sent_at is None


def test_reset_answer_route_requires_login(client, guest):
    response = client.post(f"/admin/guests/{guest.id}/reset-answer")
    assert response.status_code == 302
    assert "/admin/login" in response.location


def test_details_requires_email_when_missing(client, app):
    from app.extensions import db
    from app.models import Guest

    guest = Guest(first_name="Marcel", last_name="Petit", phone="+33612345678")
    db.session.add(guest)
    db.session.commit()

    response = client.post(
        f"/r/{guest.token}/details",
        data={"dietary_notes": "Rien de particulier"},
    )
    assert response.status_code == 200
    assert "renseigner votre e-mail".encode() in response.data

    response = client.post(
        f"/r/{guest.token}/details",
        data={"dietary_notes": "Rien de particulier", "email": "marcel@example.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    refreshed = Guest.query.filter_by(token=guest.token).first()
    assert refreshed.email == "marcel@example.com"


def test_details_does_not_require_email_when_present(client, guest):
    response = client.post(
        f"/r/{guest.token}/details",
        data={"dietary_notes": "Rien de particulier"},
        follow_redirects=True,
    )
    assert response.status_code == 200
