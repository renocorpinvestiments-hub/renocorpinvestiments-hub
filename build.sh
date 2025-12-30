#!/usr/bin/env bash
set -e

# Install Python dependencies only
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
