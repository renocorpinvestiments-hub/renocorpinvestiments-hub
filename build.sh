#!/usr/bin/env bash
set -e

pip install -r requirements.txt

python manage.py makemigrations accounts
python manage.py makemigrations

python manage.py migrate accounts
python manage.py migrate
