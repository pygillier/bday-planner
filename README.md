<div align="center">

# Birthday planner

**Simple RSVPs for any birthday party, easy enough for every guest, including grandparents.**

[![Publish](https://github.com/pygillier/bday-planner/actions/workflows/publish.yml/badge.svg)](https://github.com/pygillier/bday-planner/actions/workflows/publish.yml)
![Python 3.14](https://img.shields.io/badge/python-3.14-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-black?logo=flask)
![PostgreSQL](https://img.shields.io/badge/postgresql-336791?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)

</div>

Originally built for an 80th birthday, it works for any birthday or small celebration.

The organizer pre-registers the guest list. Each guest receives a personal link (no login, no password) where they confirm attendance, note allergies or dietary needs, and add accompanying guests. The organizer runs everything from an admin backend: guest list, invitations, response dashboard, and a caterer-ready CSV export.

Guests may be elderly or non-technical, so the guest flow is built around that: one simple page per step, large buttons, free-text fields, and a link that can be reopened at any time to review or change an answer.

## Table of contents

- [How it works](#how-it-works)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Development](#development)
- [Deploying](#deploying)
- [Project layout](#project-layout)

## How it works

1. **The organizer** logs into `/admin` and adds guests one by one or imports a CSV.
2. **Invitations** go out by e-mail or SMS, only when the organizer clicks send. Nothing is sent automatically.
3. **Each guest** opens their personal link, answers in a few taps, and can come back to change their mind.
4. **The organizer** follows responses on the dashboard and exports a CSV for the caterer.

## Features

### For guests

- Confirm or decline in one tap
- Free-text dietary notes: no menus, no checkboxes
- Add accompanying guests, with no name needed, only their own dietary notes
- Zero login: an unguessable personal link is the only credential
- Mobile-first design, French-only

### For the organizer

- Guest CRUD, plus bulk CSV import with de-duplication
- Editable invitation templates (`{prenom}`, `{nom}`, `{lien}` placeholders) for e-mail ([Resend](https://resend.com)) and SMS ([Twilio](https://www.twilio.com)), with live preview and test send
- Single or bulk invitation sending, over whichever channel each guest has contact info for
- Dashboard with headcount stats
- Caterer-ready CSV export
- Link regeneration if a guest's link leaks
- Admin login through OIDC against a self-hosted [Pocket ID](https://github.com/pocket-id/pocket-id) instance (authorization-code flow + PKCE), with no local passwords

## Tech stack

| Layer | Choice |
| --- | --- |
| Web | Flask, Flask-WTF, Flask-SQLAlchemy, Flask-Migrate |
| Database | PostgreSQL (psycopg 3) |
| Auth | Authlib, OIDC with Pocket ID |
| Messaging | Resend (e-mail), Twilio (SMS) |
| Tooling | uv, ruff, pytest, go-task |
| Runtime | Python 3.14, Docker Compose |

## Getting started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose
- [Task](https://taskfile.dev) (`go-task`)

### Run it locally

```bash
cp .env.example .env   # then fill in real values, see Configuration
task up
```

`task up` builds the image, starts Postgres, and runs pending migrations on boot. The app is then at <http://localhost:8000>. Log into `/admin` with Pocket ID and start adding guests.

## Configuration

Everything is configured through `.env`, which is git-ignored and must never be committed. `.env.example` is the template.

| Variable | Purpose |
| --- | --- |
| `FLASK_SECRET_KEY` | Any long random string: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_*`, `DATABASE_URL` | Database connection. The defaults are fine locally. |
| `RESEND_API_KEY`, `RESEND_FROM_EMAIL` | From your [Resend](https://resend.com) account, using a domain you've verified there |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | From your [Twilio](https://www.twilio.com) account, for SMS invitations to guests who have a phone number but no e-mail |
| `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | From your Pocket ID instance. Register `https://<your-domain>/admin/auth/callback` as an allowed redirect URI. |

> [!NOTE]
> Any successful Pocket ID login is granted admin access: there is deliberately no allow-list. Only point the app at an OIDC instance whose users you trust.

## Development

Every command goes through `task`; run `task --list` for the full list.

| Command | Description |
| --- | --- |
| `task up` / `task down` | Start / stop the stack |
| `task logs` | Tail the web logs |
| `task migrate` | Apply pending migrations |
| `task makemigration -- "message"` | Generate a migration after editing `app/models.py` |
| `task shell` / `task dbshell` | Flask shell / `psql` |
| `task test` | Run the test suite |
| `task lint` / `task fmt` | Lint / format with ruff |
| `task precommit-install` | Install the pre-commit hook (once per clone) |

Tests run against in-memory SQLite, so `uv sync --group dev && pytest` also works without Docker for a quick check.

## Deploying

Production runs from the container image published to GHCR on every version tag, not from source.

1. On the Docker host, copy `docker-compose.prod.yml` and a filled-in `.env` with real Resend, Twilio, Pocket ID and Postgres credentials.
2. Pull and start the stack:

   ```bash
   task deploy
   ```

   This pulls `ghcr.io/pygillier/bday-planner:latest` and (re)starts `web` and `db`, running migrations on boot. Re-run it after each release.
3. Put it behind a reverse proxy with TLS (Caddy, Traefik, nginx…). That isn't included here. `SESSION_COOKIE_SECURE` is on outside local dev, so admin login requires HTTPS.

### Releasing a new version

```bash
task tag -- patch   # or: minor / major
```

This bumps the latest `vX.Y.Z` git tag per [semver](https://semver.org) and pushes it. The [publish workflow](.github/workflows/publish.yml) then builds the image, pushes it to GHCR (tagged with the version plus rolling `major.minor`, `major` and `latest`), and creates a GitHub release with the image reference and an auto-generated changelog.

## Project layout

```
app/
  admin/    OIDC-protected backend: guests, CSV import/export, templates, dashboard
  guest/    unauthenticated, token-based RSVP flow
migrations/ Alembic migrations
tests/      pytest suite
```

See [AGENTS.md](AGENTS.md) for the full breakdown, key design decisions, and conventions. It's useful for humans and AI coding agents alike.
