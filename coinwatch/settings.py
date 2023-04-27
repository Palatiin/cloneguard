# settings.py

import os

import structlog


class FileWriterProcessor:
    def __init__(self, filename: str):
        self.filename = filename

    def __call__(self, _, __, event_dict):
        with open(self.filename, "a") as f:
            message = f"{event_dict['timestamp']} [{event_dict['level']: <9}] {event_dict['event']}\n"
            f.write(message)
        return message


def configure_logging(filename: str | None = None):
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
    ]
    if filename:
        processors.append(FileWriterProcessor(filename))
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


ENV = os.getenv("ENVIRONMENT")

GITHUB_API_ACCESS_TOKEN = os.getenv("GITHUB_API_ACCESS_TOKEN")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0"

CACHE_PATH = "coinwatch/_cache"

CONTEXT_LINES = 5
THRESHOLD = 0.25
REWARD = 0.95

PG_USER = os.getenv("PG_USER", "admin")
PG_PASS = os.getenv("PG_PASS", "postgres")
PG_HOST = os.getenv("PG_HOST", "host.docker.internal")
PG_PORT = os.getenv("PG_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

SMTP_LOGIN = os.getenv("SMTP_LOGIN")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

timestamp: int | None = None
