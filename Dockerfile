FROM python:3.12-slim-bullseye

ENV PIP_ROOT_USER_ACTION=ignore

ADD . /app
RUN pip install --upgrade pip && pip install -r /app/requirements.txt
WORKDIR /app
ENTRYPOINT /app/entrypoint.sh
