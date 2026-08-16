import csv
import io
from dataclasses import dataclass, field

from app.extensions import db
from app.models import Guest

COLUMN_ALIASES = {
    "first_name": {"first_name", "prénom", "prenom"},
    "last_name": {"last_name", "nom"},
    "email": {"email", "e-mail", "mail", "courriel"},
    "phone": {"phone", "téléphone", "telephone", "tél", "tel"},
}


@dataclass
class ImportResult:
    added: int = 0
    skipped_duplicate: int = 0
    errors: list = field(default_factory=list)


def _normalize_headers(fieldnames):
    mapping = {}
    for raw in fieldnames or []:
        key = raw.strip().lower()
        for canonical, aliases in COLUMN_ALIASES.items():
            if key in aliases:
                mapping[raw] = canonical
                break
    return mapping


def import_guests_from_csv(raw_bytes: bytes) -> ImportResult:
    """Parse a CSV of guests and create new Guest rows.

    Accepts French or English column headers (Prénom/first_name,
    Nom/last_name, E-mail/email, Téléphone/phone). Prénom and Nom are
    required; rows matching an existing guest by (first_name, last_name),
    case-insensitively, are skipped rather than duplicated.
    """
    result = ImportResult()

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        result.errors.append("Fichier illisible : encodage non reconnu (utilisez de l'UTF-8).")
        return result

    reader = csv.DictReader(io.StringIO(text))
    header_map = _normalize_headers(reader.fieldnames)

    if "first_name" not in header_map.values() or "last_name" not in header_map.values():
        result.errors.append(
            "Colonnes manquantes : le fichier doit contenir au moins « Prénom » et « Nom »."
        )
        return result

    existing = {
        (g.first_name.strip().lower(), g.last_name.strip().lower()) for g in Guest.query.all()
    }

    for line_number, row in enumerate(reader, start=2):
        data = {}
        for raw_key, value in row.items():
            canonical = header_map.get(raw_key)
            if canonical:
                data[canonical] = (value or "").strip()

        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        if not first_name or not last_name:
            if any(data.values()):
                result.errors.append(f"Ligne {line_number} : prénom et nom requis, ligne ignorée.")
            continue

        key = (first_name.lower(), last_name.lower())
        if key in existing:
            result.skipped_duplicate += 1
            continue

        db.session.add(
            Guest(
                first_name=first_name,
                last_name=last_name,
                email=data.get("email") or None,
                phone=data.get("phone") or None,
            )
        )
        existing.add(key)
        result.added += 1

    db.session.commit()
    return result
