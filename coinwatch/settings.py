# settings.py

import os

GITHUB_API_ACCESS_TOKEN = os.getenv("GITHUB_API_ACCESS_TOKEN")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0"

CONTEXT_LINES = 5
THRESHOLD = 0.25
REWARD = 0.95

PG_USER = os.getenv("PG_USER", "")
PG_PASS = os.getenv("PG_PASS", "")
PG_HOST = os.getenv("PG_HOST", "")
PG_PORT = os.getenv("PG_PORT", 5432)
DB_NAME = os.getenv("DB_NAME", "")
