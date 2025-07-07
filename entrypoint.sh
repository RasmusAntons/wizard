#!/bin/bash

alembic upgrade head
python manage.py init
if [[ "$DEBUG" = "true" ||  "$DEBUG" = "1" ]]; then
  python manage.py run --host 0.0.0.0 --port 80 --debug
else
  python manage.py run --host 0.0.0.0 --port 80
fi
