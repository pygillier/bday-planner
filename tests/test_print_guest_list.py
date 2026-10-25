from datetime import datetime

from app.extensions import db
from app.models import EventOption, Guest, PlusOne


def test_print_list_requires_login(client):
    assert client.get("/admin/guests/print").status_code == 302


def test_print_list_shows_confirmed_guests_with_notes_and_totals(admin_client, app):
    confirmed = Guest(
        first_name="Jeanne",
        last_name="Dupont",
        rsvp_status="confirmed",
        dietary_notes="Sans gluten",
    )
    confirmed.plus_ones = [PlusOne(dietary_notes="Arachides"), PlusOne()]
    other_date = Guest(first_name="Marc", last_name="Autre", rsvp_status="confirmed")
    chosen = EventOption(starts_at=datetime(2026, 9, 12, 15, 0), is_chosen=True)
    other = EventOption(starts_at=datetime(2026, 9, 13, 15, 0))
    confirmed.event_options = [chosen]
    other_date.event_options = [other]
    declined = Guest(first_name="Paul", last_name="Martin", rsvp_status="declined")
    pending = Guest(first_name="Luc", last_name="Durand")
    db.session.add_all([confirmed, other_date, declined, pending])
    db.session.commit()

    html = admin_client.get("/admin/guests/print").get_data(as_text=True)

    assert "DUPONT Jeanne" in html
    assert "Sans gluten" in html
    assert "Accompagnant 1 :</span> Arachides" in html
    assert "1 invité·e·s confirmé·e·s + 2 accompagnant·e·s = 3 personnes" in html
    assert "AUTRE" not in html
    assert "MARTIN" not in html
    assert "DURAND" not in html


def test_print_list_redirects_without_chosen_date(admin_client, guest):
    response = admin_client.get("/admin/guests/print")
    assert response.status_code == 302
    assert "/admin/guests" in response.headers["Location"]


def test_print_button_only_shown_when_date_chosen(admin_client, app):
    assert b"/admin/guests/print" not in admin_client.get("/admin/guests").data
    db.session.add(EventOption(starts_at=datetime(2026, 9, 12, 15, 0), is_chosen=True))
    db.session.commit()
    assert b"/admin/guests/print" in admin_client.get("/admin/guests").data
