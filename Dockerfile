FROM python:3.12 AS requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.12
LABEL maintainer="Vitalii Vinnychenko <vitalii@mealhow.ai>"

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get -y install --no-install-recommends gcc mono-mcs libffi-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY ./sa.json /tmp/sa-artifact-registry.json
ENV GOOGLE_APPLICATION_CREDENTIALS=/tmp/sa-artifact-registry.json

WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt
RUN pip install --upgrade pip
RUN pip install keyrings.google-artifactregistry-auth
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./app

ENV PORT 1234

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT}", "--workers", "1"]
