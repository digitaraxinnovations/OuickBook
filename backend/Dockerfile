# Ledgerly API (FastAPI). Built by the root docker-compose.yml.
# Settings come from environment variables - nothing is baked into the image.

# Same Python version as development and the tests.
FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install packages first so code changes don't reinstall them.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker ./docker

# Run as a normal user, not root.
RUN useradd --create-home --uid 1000 ledgerly && chmod +x docker/*.sh
USER ledgerly

EXPOSE 8000

# The API: brings the database up to date, then starts the web server.
# The scheduler service reuses this image with docker/scheduler.sh instead.
CMD ["./docker/start-api.sh"]
