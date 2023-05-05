# File: Dockerfile
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023/03/15
# Description: Dockerfile for CloneGuard

# Base image
FROM python:3.11-slim

# install system dependencies
RUN apt-get update -yqq && \
    apt-get install -yqq curl git default-jdk cron && \
	rm -rf /var/lib/apt/lists/*

# install poetry
RUN python -m pip install --upgrade pip
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/usr/local python3 - && \
	poetry config virtualenvs.create false

# set working directory
WORKDIR /app
ENV PYTHONPATH "/app:${PYTHONPATH}"

# install python dependencies
COPY pyproject.toml poetry.lock /app/
RUN poetry check && \
	poetry show --tree && \
	poetry install --no-root

# include source code
COPY ./cloneguard /app/cloneguard

# configure git
RUN echo "[safe]" >> ~/.gitconfig && \
    echo "    directory = *" >> ~/.gitconfig

# easier access to cli
RUN echo "#!/bin/sh" > cli && \
    echo "exec python3 cloneguard.cli $@" >> cli && \
	chmod +x cli

# initiliaze nltk, download data sets
RUN python3 -m cloneguard.utils.nltk_init
