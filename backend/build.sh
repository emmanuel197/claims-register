#!/usr/bin/env bash
# Render build step: install, collect static, migrate, seed (idempotent).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_claims
