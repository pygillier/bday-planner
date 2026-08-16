# 80 ans 🎉

A small web app for managing RSVPs to an 80th birthday party.

The organizer pre-registers the guest list. Each guest gets a personal link — no login, no password — where they confirm attendance, note allergies/dietary needs, and add accompanying guests. The organizer manages everything from an admin backend: guest list, invitation emails, response dashboard, and a caterer-ready CSV export.

Built for a non-technical, largely elderly guest list: the guest-facing flow is a single page per step, large buttons, free-text everywhere, and the same link can always be reopened to review or change an answer.

## Features

- **Guest RSVP**: confirm/decline, free-text dietary notes, add accompanying guests (no name needed, just their own dietary notes)
- **Admin backend**: add/edit/remove guests, send invitations (single or bulk) via [Resend](https://resend.com), dashboard with headcount stats, CSV export
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
   - `OIDC_ISSUER` / `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` — from your Pocket ID instance; register `https://<your-domain>/admin/auth/callback` as the client's allowed redirect URI

2. Start everything:

   ```bash
   task up
   ```

   This builds the image, starts Postgres, and runs pending migrations automatically. The app is then available at `http://localhost:8000`.

3. Log into `/admin` with Pocket ID and start adding guests.

See `Taskfile.yml` (`task --list`) for the rest of the day-to-day commands: `migrate`, `makemigration`, `shell`, `dbshell`, `test`, `lint`, `fmt`.

## Deploying

The Compose setup is hosting-agnostic — it works on any Docker host. Put it behind a reverse proxy with TLS (Caddy, Traefik, nginx…); that's not included here. `SESSION_COOKIE_SECURE` is enabled outside of local dev, so admin login requires HTTPS in production.

## Project layout

See [AGENTS.md](AGENTS.md) for the full breakdown of the codebase structure, key design decisions, and conventions — useful for both humans and AI coding agents picking this up later.
