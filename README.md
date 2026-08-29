# 80 ans 🎉

A small web app for managing RSVPs to an 80th birthday party.

The organizer pre-registers the guest list. Each guest gets a personal link — no login, no password — where they confirm attendance, note allergies/dietary needs, and add accompanying guests. The organizer manages everything from an admin backend: guest list, invitation emails, response dashboard, and a caterer-ready CSV export.

Built for a non-technical, largely elderly guest list: the guest-facing flow is a single page per step, large buttons, free-text everywhere, and the same link can always be reopened to review or change an answer.

## Features

- **Guest RSVP**: confirm/decline, free-text dietary notes, add accompanying guests (no name needed, just their own dietary notes)
- **Admin backend**: add/edit/remove guests (one by one or bulk CSV import), editable invitation templates (e-mail via [Resend](https://resend.com), SMS via [Twilio](https://www.twilio.com), both with a live preview and test-send), send invitations (single or bulk, over whichever channel each guest has contact info for), dashboard with headcount stats, CSV export
- **Admin login** via OIDC against a self-hosted [Pocket ID](https://github.com/pocket-id/pocket-id) instance (Authlib, authorization-code flow + PKCE) — no local passwords
- French-only UI

## Stack

Flask · PostgreSQL · SQLAlchemy · Docker Compose · Python 3.14

## Getting started

Requires [Docker](https://docs.docker.com/get-docker/) and [Task](https://taskfile.dev) (`go-task`).

1. Copy the environment template and fill in real values:

   ```bash
   cp .env.example .env
   ```

   You'll need:
   - `FLASK_SECRET_KEY` — any long random string (`python -c "import secrets; print(secrets.token_hex(32))"`)
   - `POSTGRES_*` / `DATABASE_URL` — can keep the defaults for local use
   - `RESEND_API_KEY` / `RESEND_FROM_EMAIL` — from your [Resend](https://resend.com) account, using a domain you've verified there
   - `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` — from your [Twilio](https://www.twilio.com) account, for SMS invitations to guests with a phone number but no e-mail
   - `OIDC_ISSUER` / `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` — from your Pocket ID instance; register `https://<your-domain>/admin/auth/callback` as the client's allowed redirect URI

2. Start everything:

   ```bash
   task up
   ```

   This builds the image, starts Postgres, and runs pending migrations automatically. The app is then available at `http://localhost:8000`.

3. Log into `/admin` with Pocket ID and start adding guests.

See `Taskfile.yml` (`task --list`) for the rest of the day-to-day commands: `migrate`, `makemigration`, `shell`, `dbshell`, `test`, `lint`, `fmt`.

## Deploying

The app is published as a container image to GHCR on every version tag (see below), and production runs off that image rather than building from source.

1. On the Docker host, copy `docker-compose.prod.yml` and a filled-in `.env` (same variables as local `.env`, but pointing at real Resend/Pocket ID/Postgres credentials, with `SESSION_COOKIE_SECURE` implications in mind — see step 3 below).
2. Pull and start the stack:

   ```bash
   task deploy
   ```

   This pulls `ghcr.io/pygillier/bday-planner:latest` and (re)starts `web` + `db` via `docker-compose.prod.yml`, running pending migrations automatically on boot. Re-run `task deploy` after each release to update.
3. Put it behind a reverse proxy with TLS (Caddy, Traefik, nginx…) — that's not included here. `SESSION_COOKIE_SECURE` is enabled outside of local dev, so admin login requires HTTPS in production.

### Releasing a new version

```bash
task tag -- patch   # or: minor / major
```

This bumps the last `vX.Y.Z` git tag per [semver](https://semver.org) and pushes it, which triggers a GitHub Actions workflow ([.github/workflows/publish.yml](.github/workflows/publish.yml)) that builds the image, pushes it to GHCR tagged with the version (plus rolling `major.minor`, `major`, and `latest` tags), and creates a GitHub release with the image reference and auto-generated changelog.

## Project layout

See [AGENTS.md](AGENTS.md) for the full breakdown of the codebase structure, key design decisions, and conventions — useful for both humans and AI coding agents picking this up later.
