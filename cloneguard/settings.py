# File: settings.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2022-08-06
# Description: Configurations file.

import os

import structlog


class FileWriterProcessor:
    def __init__(self, filename: str):
        self.filename = filename

    def __call__(self, _, __, event_dict):
        with open(self.filename, "a") as f:
            other_keys = self.format_other_keys(event_dict)
            message = (
                f"{event_dict['timestamp']} [{event_dict['level']: <9}] {event_dict['event']}"
                f"{'    ' + other_keys if other_keys else ''}\n"
            )
            f.write(message)
        return message

    @staticmethod
    def format_other_keys(event_dict):
        other_keys = [
            f"{key}={value}" for key, value in event_dict.items() if key not in {"timestamp", "level", "event"}
        ]
        return " ".join(other_keys)


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

CACHE_PATH = "cloneguard/_cache"

CONTEXT_LINES = 5
THRESHOLD = 0.25
REWARD = 0.95

# PostgreSQL configuration
PG_USER = os.getenv("PG_USER", "admin")
PG_PASS = os.getenv("PG_PASS", "postgres")
PG_HOST = os.getenv("PG_HOST", "host.docker.internal")
PG_PORT = os.getenv("PG_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}")

# Postman class SMTP configuration
SMTP_LOGIN = os.getenv("SMTP_LOGIN")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# discovery scan recipients
NOTIFY_LIST = ["xremen01@stud.fit.vutbr.cz"]

timestamp: int | None = None
