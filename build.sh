#!/usr/bin/env bash

# 1. Install requirements
pip install -r requirements.txt

# 2. Make migrations for accounts first
python manage.py makemigrations accounts

# 3. Make migrations for other apps, including admin_panel
python manage.py makemigrations

# 4. Apply migrations in order
python manage.py migrate accounts
python manage.py migrate

# 5. Optional: collect static files (skip if on free tier)
# python manage.py collectstatic --noinput
