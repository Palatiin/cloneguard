# settings.py

import os

from coinwatch.utils import Logger

logger = Logger()

GITHUB_API_ACCESS_TOKEN = os.getenv("GITHUB_API_ACCESS_TOKEN")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0"
