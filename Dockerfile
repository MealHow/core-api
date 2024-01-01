FROM python:3.12-slim
LABEL maintainer="Vitalii Vinnychenko <vitalii@mealhow.ai>"

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

ENV POETRY_VERSION=1.7.0
RUN apt-get update && \
    apt-get -y install --no-install-recommends gcc mono-mcs libffi-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN pip install -U pip \
    pip install poetry==$POETRY_VERSION
RUN poetry config virtualenvs.create false

COPY ./sa.json /tmp/sa-artifact-registry.json
ENV GOOGLE_APPLICATION_CREDENTIALS=/tmp/sa-artifact-registry.json

COPY poetry.lock pyproject.toml /app/
WORKDIR /app

RUN poetry self add "keyrings.google-artifactregistry-auth"
RUN poetry install --no-interaction --no-ansi --no-root

COPY ./poetry.lock /app/poetry.lock
COPY ./pyproject.toml /app/pyproject.toml
COPY /src /app

EXPOSE 80

CMD exec poetry run uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1
