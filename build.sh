#!/usr/bin/env bash
set -e

# Install Python dependencies only
pip install -r requirements.txt
python manage.py repair_accounts
# Skip migrations during build — the DB is unreachable at build time
