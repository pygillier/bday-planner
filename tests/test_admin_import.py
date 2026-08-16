import io

from app.admin.csv_import import import_guests_from_csv
from app.models import Guest


def test_import_creates_guests(app):
    csv_bytes = "Prénom,Nom,E-mail,Téléphone\nJeanne,Dupont,jeanne@example.com,0102030405\n".encode()
    result = import_guests_from_csv(csv_bytes)

    assert result.added == 1
    assert result.skipped_duplicate == 0
    assert result.errors == []
    guest = Guest.query.filter_by(first_name="Jeanne", last_name="Dupont").first()
    assert guest is not None
    assert guest.email == "jeanne@example.com"
    assert guest.phone == "0102030405"


def test_import_accepts_english_headers(app):
    csv_bytes = b"first_name,last_name,email\nPaul,Martin,paul@example.com\n"
    result = import_guests_from_csv(csv_bytes)

    assert result.added == 1
    assert Guest.query.filter_by(first_name="Paul").first() is not None


def test_import_skips_existing_duplicates(app, guest):
    csv_bytes = "Prénom,Nom\nJeanne,Dupont\nNouveau,Invité\n".encode()
    result = import_guests_from_csv(csv_bytes)

    assert result.added == 1
    assert result.skipped_duplicate == 1
    assert Guest.query.count() == 2


def test_import_reports_missing_required_columns(app):
    csv_bytes = b"E-mail\njeanne@example.com\n"
    result = import_guests_from_csv(csv_bytes)

    assert result.added == 0
    assert len(result.errors) == 1
    assert Guest.query.count() == 0


def test_import_flags_rows_missing_name(app):
    csv_bytes = "Prénom,Nom,E-mail\n,,orphan@example.com\nValid,Row,\n".encode()
    result = import_guests_from_csv(csv_bytes)

    assert result.added == 1
    assert len(result.errors) == 1
    assert "Ligne 2" in result.errors[0]


def test_import_route_requires_login(client):
    response = client.get("/admin/guests/import")
    assert response.status_code == 302


def test_import_route_creates_guest(admin_client):
    data = {
        "csv_file": (io.BytesIO("Prénom,Nom\nAlice,Martin\n".encode()), "guests.csv"),
    }
    response = admin_client.post(
        "/admin/guests/import", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 302
    assert Guest.query.filter_by(first_name="Alice").first() is not None


def test_import_route_rejects_non_csv(admin_client):
    data = {
        "csv_file": (io.BytesIO(b"not a csv"), "guests.txt"),
    }
    response = admin_client.post(
        "/admin/guests/import", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 200
    assert Guest.query.count() == 0
