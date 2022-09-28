# logger.py

from enum import Enum


class Color(str, Enum):
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    RESET = "\033[39m"


class LogType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Logger:
    """Implementation of a custom logger."""

    def __init__(self, v: bool = False):
        self.verbose: bool = v

    def info(self, message: str, v: bool = False):
        self.log(message, LogType.INFO, v)

    def warning(self, message: str, v: bool = False):
        self.log(message, LogType.WARNING, v)

    def error(self, message: str, v: bool = False):
        self.log(message, LogType.ERROR, v)

    def log(self, message: str = "", log_type: LogType = LogType.INFO, v: bool = False):
        if not v and not self.verbose:
            return

        switcher = {
            LogType.INFO: Color.GREEN.value,
            LogType.WARNING: Color.YELLOW.value,
            LogType.ERROR: Color.RED.value,
        }
        log_type_color = switcher[log_type]
        bold = "\033[1m"
        print(f"{bold}[{log_type_color}{log_type:7}{Color.RESET}] {message}")
