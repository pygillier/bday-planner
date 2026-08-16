# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this is

A small Flask + PostgreSQL app for managing RSVPs to an 80th birthday party. The organizer pre-registers guests via an admin backend; guests (many elderly, non-technical) confirm attendance through a personal link with zero login. French-only UI. See `/home/pygillier/.claude/plans/i-need-to-create-twinkly-puzzle.md` for the original design plan and rationale if it still exists — otherwise this file and the code are the source of truth.

## Stack

- Python 3.14, Flask, Flask-SQLAlchemy, Flask-Migrate (Alembic), Flask-WTF
- PostgreSQL (psycopg3)
- Authlib for OIDC (admin auth against a self-hosted **Pocket ID** instance, authorization-code flow + PKCE)
- Resend for transactional email (invitations)
- Docker Compose for local dev and deployment; `Taskfile.yml` (go-task) as the single command entrypoint
- ruff for lint/format, pytest for tests

## Project structure

```
app/
  __init__.py        app factory: create_app()
  config.py           Config (env-driven) + TestConfig (sqlite, CSRF off)
  extensions.py         db, migrate, csrf, oauth singletons
  models.py              Guest, PlusOne, InvitationLog
  emails.py                Resend integration
  admin/                    OIDC-protected blueprint: guest CRUD, CSV import/export, dashboard
    csv_import.py             pure parsing/dedup logic for bulk guest import, unit-testable
  guest/                     unauthenticated blueprint: token-based RSVP flow
  templates/, static/         guest side is mobile-first with the "80 ANS" design identity;
                               admin side is desktop-first, plain
migrations/                Alembic migrations (generated, committed)
tests/                      pytest, run against an in-memory sqlite DB via TestConfig
```

## Key design decisions (don't relitigate without asking)

- **Guest access**: unguessable `secrets.token_urlsafe(32)` token in the URL is the only credential. No guest accounts, no passwords, no guest-side OIDC.
- **Plus-ones**: no name field, ever — just one free-text dietary-notes row per accompanying guest, identified by order ("Accompagnant 1", "Accompagnant 2"). This was an explicit, deliberate simplification.
- **Allergy/dietary capture**: free text only. No structured menu-choice enum, no checkboxes.
- **Admin auth**: any successfully authenticated Pocket ID login is granted admin access — there is intentionally no allow-list/authorization table. `session["admin_sub"]` is the only gate (`app/admin/auth.py` + the blueprint's `before_request` in `app/admin/routes.py`).
- **Invitations**: sent only when the organizer explicitly clicks send (single or bulk) — never automatically on guest creation.
- **No token expiry**: links are valid indefinitely; `regenerate-link` is the manual mitigation if one leaks.

## Dev workflow

All commands go through `task` (see `Taskfile.yml`):

```
task up             # build + start app and db (runs migrations automatically on boot)
task down
task logs
task migrate         # flask db upgrade
task makemigration -- "message"   # flask db migrate -m "message"
task shell            # flask shell in the running container
task dbshell            # psql
task test                 # pytest
task lint                  # ruff check
task fmt                    # ruff format
```

Requires `docker` and `task` (go-task) locally. There is no local venv workflow expected — everything runs against the Compose stack. A `.env` (git-ignored, see `.env.example`) is required; it is **not** committed and must never be added to git.

### Generating a fresh migration after model changes

Editing `app/models.py` alone does not update the database. Run `task makemigration -- "description"` then `task migrate` (or just restart the stack — the `web` service runs `flask db upgrade` on boot). Migrations are committed to the repo under `migrations/versions/`.

### Testing without Docker

`tests/conftest.py` builds the app with `TestConfig` (in-memory SQLite, CSRF disabled), so `pytest` can run directly against a local Python 3.14 + `pip install -r requirements-dev.txt` environment if you don't want to go through Docker for a quick check. `task test` is the canonical way, though.

## Conventions

- Keep the guest-facing surface (`app/guest/`) friction-free: no new required fields, no multi-step flows, no client-side JS dependency for core functionality (progressive enhancement only).
- Keep the admin surface (`app/admin/`) dense and utilitarian — it's a tool for one tech-comfortable organizer, not a polished product.
- French strings live inline in templates (no i18n framework — single-language by design).
- CSRF protection is global (Flask-WTF `CSRFProtect`); every POST form needs a `csrf_token` field/hidden input.
- Datetimes: use `app.models.utcnow()` (timezone-aware), not `datetime.utcnow()` (deprecated).
