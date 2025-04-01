#!/bin/bash

# Wait for Postgres to be available
echo "Waiting for PostgreSQL..."
while ! nc -z postgres-db 5432; do
  sleep 1
done

echo "PostgreSQL started"

# Run Alembic migrations
alembic upgrade head

# Start FastAPI app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
