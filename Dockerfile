FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (separate layer for cache efficiency)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source
COPY app/ app/
COPY migrations/ migrations/
COPY config.py wsgi.py docker-entrypoint.sh ./

# Run as non-root
RUN useradd -m -u 1000 ramtime \
    && mkdir -p instance \
    && chown -R ramtime:ramtime /app
USER ramtime

ENV FLASK_ENV=production \
    PORT=8000

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
