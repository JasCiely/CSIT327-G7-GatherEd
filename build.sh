#!/usr/bin/env bash
set -0 errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate