# File: src/common.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-03-19
# Description: Implementation of line/file filters and logging decorator.

import os
import re
from pathlib import Path

import structlog


class Filter(object):
    extensions = {"py", "c", "cpp", "go", "h", "hpp"}
    _re_lang_comment = {
        "py": r'\s*(#|""").*?{}',
        "c": r"\s*(/\*|//|/\*\*).*?{}",
        "h": r"\s*(/\*|//|/\*\*).*?{}",
        "cpp": r"\s*(/\*|//|/\*\*).*?{}",
        "hpp": r"\s*(/\*|//|/\*\*).*?{}",
        "go": r"\s*(//|/\*).*?{}",
        "hs": r"\s*(--|{-).*?{}",
    }
    _re_brackets = re.compile(r"\s*[\[\](){}]+\s*(?:[;,]\s*)?$")
    __c_keywords = {
        "auto",
        "bool",
        "char",
        "const",
        "false",
        "float",
        "int",
        "long",
        "return",
        "short",
        "signed",
        "unsigned",
        "void",
    }
    _lang_frequent_keywords = {
        "py": {
            "and",
            "as",
            "break",
            "elif",
            "else",
            "False",
            "for",
            "if",
            "in",
            "not",
            "or",
            "return",
            "True",
            "while",
        },
        "c": __c_keywords,
        "cpp": __c_keywords,
        "h": __c_keywords,
        "hpp": __c_keywords,
        "go": {"uint64", "var"},
    }

    @classmethod
    def line(cls, line: str, filename: str = "", file_ext: str = "", keyword: str = "") -> bool:
        return (
            cls._in_test(filename)
            | cls._is_blank(line)
            | cls._in_comment(line, file_ext, keyword)
            | cls._is_single_bracket(line)
        )

    @classmethod
    def file(cls, filename: str, file_ext: str = None) -> bool:
        file_ext = file_ext or Path(filename).suffix[1:]
        return cls._in_test(filename) | bool(file_ext not in cls.extensions)

    @staticmethod
    def _in_test(filename: str) -> bool:
        if not filename:
            return False
        return "test" in filename.lower()

    @classmethod
    def _in_comment(cls, line: str, file_ext: str, keyword: str = "") -> bool:
        if not file_ext:
            return False
        return bool(re.match(cls._re_lang_comment[file_ext].format(keyword), line, flags=re.S))

    @staticmethod
    def _is_blank(line: str) -> bool:
        return not line.strip()

    @classmethod
    def _is_single_bracket(cls, line: str) -> bool:
        return bool(cls._re_brackets.match(line))


def log_wrapper(func):
    logger = structlog.get_logger(func.__name__)
    pid = os.getpid()

    def inner(*args, **kwargs):
        logger.info(f"{func.__qualname__}: Start...", pid=pid)
        result = func(*args, **kwargs)
        logger.info(f"{func.__qualname__}: Done.", pid=pid)
        return result

    return inner