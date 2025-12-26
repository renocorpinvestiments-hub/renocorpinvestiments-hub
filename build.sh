#!/usr/bin/env bash

# Install requirements
pip install -r requirements.txt

# Make migrations (optional if you already have migration files)
python manage.py makemigrations accounts

# Apply migrations (create tables in the database)
python manage.py migrate

# NOTE: Skip collectstatic on free tier
# If you have static files, Django can serve them directly via STATIC_URL
# python manage.py collectstatic --noinput
