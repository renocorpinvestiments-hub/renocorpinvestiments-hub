#!/usr/bin/env bash
# build.sh — Run on Render during deploy

# Exit immediately if a command fails
set -e

# 1️⃣ Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# 2️⃣ Make migrations (if needed)
echo "Making migrations..."
python manage.py makemigrations --noinput

# 3️⃣ Apply migrations
echo "Applying migrations..."
python manage.py migrate --noinput

echo "Build complete!"
