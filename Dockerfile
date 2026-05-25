# ---- build stage: resolve dependencies ----
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


# ---- runtime stage ----
FROM python:3.12-slim

WORKDIR /app

# Copy the pre-built venv from the builder
COPY --from=builder /app/.venv /app/.venv

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source
COPY app/ app/
COPY migrations/ migrations/
COPY config.py wsgi.py docker-entrypoint.sh ./

# Run as non-root
RUN useradd -m -u 1000 ramtime \
    && mkdir -p instance \
    && chmod +x docker-entrypoint.sh \
    && chown -R ramtime:ramtime /app
USER ramtime

ENV FLASK_ENV=production \
    PORT=8000

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
