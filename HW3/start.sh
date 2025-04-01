#!/bin/bash

echo "⏳ Waiting for Postgres..."
while ! nc -z db 5432; do
  sleep 0.5
done
echo "✅ Postgres is up!"

echo "🗂 Running Alembic migrations..."
alembic upgrade head

echo "🚀 Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
