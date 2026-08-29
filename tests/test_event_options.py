from datetime import datetime

from app.extensions import db
from app.models import EventOption, Guest


def _make_option(label=None, starts_at=None):
    option = EventOption(label=label, starts_at=starts_at or datetime(2026, 9, 12, 15, 0))
    db.session.add(option)
    db.session.commit()
    return option


def test_display_text_falls_back_to_formatted_date(app):
    option = _make_option(starts_at=datetime(2026, 9, 12, 15, 0))
    assert option.display_text == "samedi 12 septembre 2026 à 15h"


def test_display_text_uses_label_when_set(app):
    option = _make_option(label="Brunch", starts_at=datetime(2026, 9, 13, 12, 0))
    assert option.display_text.startswith("Brunch — ")


def test_event_options_route_requires_login(client):
    response = client.get("/admin/dates")
    assert response.status_code == 302


def test_admin_can_create_event_option(admin_client, app):
    response = admin_client.post(
        "/admin/dates/new",
        data={"label": "Samedi", "starts_at": "2026-09-12T15:00"},
    )
    assert response.status_code == 302
    assert EventOption.query.count() == 1
    assert EventOption.query.first().label == "Samedi"


def test_admin_can_edit_event_option(admin_client, app):
    option = _make_option(label="Samedi")
    response = admin_client.post(
        f"/admin/dates/{option.id}/edit",
        data={"label": "Dimanche", "starts_at": "2026-09-13T12:00"},
    )
    assert response.status_code == 302
    assert db.session.get(EventOption, option.id).label == "Dimanche"


def test_admin_can_delete_unused_event_option(admin_client, app):
    option = _make_option()
    response = admin_client.post(f"/admin/dates/{option.id}/delete")
    assert response.status_code == 302
    assert EventOption.query.count() == 0


def test_admin_cannot_delete_event_option_in_use(admin_client, app, guest):
    option = _make_option()
    guest.event_options = [option]
    db.session.commit()

    response = admin_client.post(f"/admin/dates/{option.id}/delete")
    assert response.status_code == 302
    assert EventOption.query.count() == 1


def test_guest_details_without_options_has_no_date_field(client, guest):
    client.post(f"/r/{guest.token}/confirmer")
    response = client.get(f"/r/{guest.token}/details")
    assert response.status_code == 200
    assert b"event_option_ids" not in response.data


def test_guest_must_choose_a_date_when_options_exist(client, guest, app):
    _make_option(label="Samedi")
    client.post(f"/r/{guest.token}/confirmer")

    response = client.post(f"/r/{guest.token}/details", data={"dietary_notes": ""})
    assert response.status_code == 200
    assert "Merci de choisir au moins une date".encode() in response.data

    refreshed = Guest.query.filter_by(token=guest.token).first()
    assert refreshed.event_options == []


def test_guest_can_choose_multiple_dates(client, guest, app):
    option_a = _make_option(label="Samedi", starts_at=datetime(2026, 9, 12, 15, 0))
    option_b = _make_option(label="Dimanche", starts_at=datetime(2026, 9, 13, 12, 0))
    client.post(f"/r/{guest.token}/confirmer")

    response = client.post(
        f"/r/{guest.token}/details",
        data={
            "dietary_notes": "",
            "event_option_ids": [str(option_a.id), str(option_b.id)],
        },
    )
    assert response.status_code == 302

    refreshed = Guest.query.filter_by(token=guest.token).first()
    assert {option.id for option in refreshed.event_options} == {option_a.id, option_b.id}


def test_dashboard_shows_most_selected_date(admin_client, app, guest):
    option_a = _make_option(label="Samedi", starts_at=datetime(2026, 9, 12, 15, 0))
    option_b = _make_option(label="Dimanche", starts_at=datetime(2026, 9, 13, 12, 0))

    guest.rsvp_status = "confirmed"
    guest.event_options = [option_a, option_b]

    other_guest = Guest(first_name="Marc", last_name="Martin", rsvp_status="confirmed")
    other_guest.event_options = [option_a]
    db.session.add(other_guest)
    db.session.commit()

    response = admin_client.get("/admin/")
    assert response.status_code == 200
    assert "Date la plus plébiscitée".encode() in response.data
    assert option_a.display_text.encode() in response.data
    assert b"2 disponibles" in response.data


def test_dashboard_hides_most_selected_date_when_nobody_available(admin_client, app, guest):
    _make_option(label="Samedi")

    response = admin_client.get("/admin/")
    assert response.status_code == 200
    assert "Date la plus plébiscitée".encode() not in response.data
