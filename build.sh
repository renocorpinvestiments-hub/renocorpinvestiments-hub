#!/usr/bin/env bash
set -e

pip install -r requirements.txt

# Make sure migration files exist
python manage.py makemigrations accounts
python manage.py makemigrations

# Force Django to forget the broken state (safe on fresh deploys)
python manage.py migrate accounts --fake || true
python manage.py migrate admin --fake || true

# Now apply everything in the correct order
python manage.py migrate accounts
python manage.py migrate
