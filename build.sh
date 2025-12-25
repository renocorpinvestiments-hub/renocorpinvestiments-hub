#!/usr/bin/env bash

# Install requirements
pip install -r requirements.txt

# Make migrations (create migration files)
python manage.py makemigrations

# Apply migrations (create tables in the database)
python manage.py migrate

# Collect static files (optional if you have static assets)
python manage.py collectstatic --noinput
