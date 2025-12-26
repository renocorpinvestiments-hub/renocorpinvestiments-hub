#!/usr/bin/env bash
set -e

pip install -r requirements.txt

# Make sure migration files exist
python manage.py makemigrations accounts
python manage.py makemigrations

# 🔥 Force-reset Django's migration history (free tier rescue)
python manage.py migrate accounts 0001 --fake || true
python manage.py migrate admin 0001 --fake || true
python manage.py migrate contenttypes 0001 --fake || true
python manage.py migrate auth 0001 --fake || true

# 🧱 Now rebuild migrations in correct order
python manage.py migrate accounts
python manage.py migrate
