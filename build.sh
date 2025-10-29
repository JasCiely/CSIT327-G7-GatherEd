#!/usr/bin/env bash
set -0 errexit

pip intall -r requirments.txt
python manage.py collectstatic --noinput
python manage.py migrate