def test_landing_shows_greeting(client, guest):
    response = client.get(f"/rsvp/{guest.token}")
    assert response.status_code == 200
    assert "Jeanne".encode() in response.data


def test_invalid_token_returns_404(client):
    response = client.get("/rsvp/does-not-exist")
    assert response.status_code == 404


def test_confirm_then_decline(client, guest):
    client.post(f"/rsvp/{guest.token}/confirmer")
    response = client.get(f"/rsvp/{guest.token}")
    assert "confirm".encode() in response.data.lower()

    client.post(f"/rsvp/{guest.token}/decliner")
    response = client.get(f"/rsvp/{guest.token}")
    assert "d\xe9clin".encode("utf-8") in response.data.lower() or b"pas pouvoir venir" in response.data


def test_add_and_remove_plus_one(client, guest, app):
    from app.models import Guest

    client.post(f"/rsvp/{guest.token}/confirmer")
    client.post(f"/rsvp/{guest.token}/details/plus-one/add")

    refreshed = Guest.query.filter_by(token=guest.token).first()
    assert len(refreshed.plus_ones) == 1

    plus_one_id = refreshed.plus_ones[0].id
    client.post(f"/rsvp/{guest.token}/details/plus-one/{plus_one_id}/remove")

    refreshed = Guest.query.filter_by(token=guest.token).first()
    assert len(refreshed.plus_ones) == 0


def test_details_requires_confirmation(client, guest):
    response = client.get(f"/rsvp/{guest.token}/details")
    assert response.status_code == 302
