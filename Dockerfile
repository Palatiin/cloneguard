FROM python:3.11-slim

RUN apt-get update -yqq && apt-get install -yqq curl

RUN python -m pip install --upgrade pip
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/usr/local python3 - && \
	poetry config virtualenvs.create false

#WORKDIR /opt
#COPY requirements.in .
#RUN pip install -r requirements.txt --ignore-installed

WORKDIR /app
ENV PYTHONPATH "/app:${PYTHONPATH}"

COPY pyproject.toml poetry.lock /app/
RUN poetry check && \
	poetry show --tree && \
	poetry install --no-root

COPY ./coinwatch /app/coinwatch

RUN python3 -m coinwatch.utils.nltk_init
