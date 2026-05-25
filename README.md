# Ramtime

Employee time-tracking web application built with Flask and SQLite.

## Features

- Clock in / clock out with current time
- Manual time entry with date, start, and end time
- Per-entry notes and minimum-hours billing rule
- Monthly log view per employee
- Admin dashboard with first-half / second-half / full-month filtering
- CSV export for payroll
- User management (add, archive, delete employees)

---

## Running with Docker

### Quick start

```bash
docker run -d \
  --name ramtime \
  -p 8000:8000 \
  -e SECRET_KEY=<your-secret-key> \
  -v ramtime-data:/app/instance \
  ghcr.io/johnramsden/ramtime:latest
```

Then open [http://localhost:8000](http://localhost:8000) and log in with:

| Username | Password |
|----------|----------|
| `admin`  | `admin`  |

> **Change the default password immediately** after first login via the Users page.

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | `dev-insecure-change-me` | Signs session cookies. Must be secret and stable across restarts. |
| `PORT` | No | `8000` | Port Gunicorn listens on inside the container. |
| `WEB_CONCURRENCY` | No | `2` | Number of Gunicorn worker processes. |
| `FLASK_ENV` | No | `production` | Set to `development` for debug mode (never in production). |

### Generating a SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Keep this value secret. If it changes, all active sessions are invalidated (everyone is logged out).

### Persistent data

The SQLite database is stored at `/app/instance/ramtime.db` inside the container. Mount a volume to persist it across container restarts:

```bash
-v ramtime-data:/app/instance
```

Or bind-mount a host directory:

```bash
-v /path/on/host:/app/instance
```

### Docker Compose example

```yaml
services:
  ramtime:
    image: ghcr.io/<your-org>/ramtime:latest
    ports:
      - "8000:8000"
    environment:
      SECRET_KEY: "change-me-to-a-random-64-char-string"
    volumes:
      - ramtime-data:/app/instance
    restart: unless-stopped

volumes:
  ramtime-data:
```

---

## Running locally (development)

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
# Install dependencies (including dev tools)
uv sync --group dev

# Install Playwright browsers for UI tests
uv run playwright install chromium

# Apply database migrations
uv run flask --app wsgi db upgrade

# Create the first admin user (interactive)
uv run flask --app wsgi seed-admin

# Start the dev server
uv run flask --app wsgi run
```

Open [http://localhost:5000](http://localhost:5000).

### Running tests

```bash
# Unit and integration tests
uv run pytest tests/unit tests/integration

# Browser / UI tests (requires Chromium)
uv run pytest tests/browser

# All tests
uv run pytest tests/
```

---

## Releasing a new version

Push a semver tag to trigger the GitHub Actions build:

```bash
git tag v1.2.3
git push origin v1.2.3
```

This builds and pushes to GHCR with tags `1.2.3`, `1.2`, and `latest`.

---

## Schema migrations

After changing models, generate and apply a migration:

```bash
uv run flask --app wsgi db migrate -m "describe the change"
uv run flask --app wsgi db upgrade
```
