#!/usr/bin/env bash
set -0 errexit

pip install -r requirments.txt
python manage.py collectstatic --noinput
python manage.py migrate