#!/bin/bash
echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --ignore-missing-source 2>/dev/null || true

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Starting Gunicorn ==="
gunicorn --bind=0.0.0.0:8000 --timeout 600 lead_system.wsgi