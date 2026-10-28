#!/usr/bin/env bash
# Build step for Render (or any host): install, collect static files, load the published aggregates.
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py load_indicators
python manage.py load_satellite
