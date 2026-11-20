#!/bin/sh
# Starts the API inside Docker: update the database, then serve.
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting the API on port 8000 with ${API_WORKERS:-2} worker(s)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${API_WORKERS:-2}" --proxy-headers
