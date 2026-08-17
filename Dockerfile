FROM ghcr.io/astral-sh/uv:0.11.18 AS uv

FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --group dev

COPY . .

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "wsgi:app"]
