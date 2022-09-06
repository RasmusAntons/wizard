#!/bin/bash

alembic upgrade head
python manage.py init
python manage.py run --host 0.0.0.0 --port 80
