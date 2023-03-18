import re


class Filter(object):
    _re_lang_comment = {
        "py": r'\s*(#|""").*?{}',
        "c": r"\s*(/\*|//|/\*\*).*?{}",
        "cpp": r"\s*(/\*|//|/\*\*).*?{}",
    }
    _re_brackets = re.compile(r"\s*[\[\](){}]\s*;?")

    @classmethod
    def line(cls, line: str, filename: str = "", file_ext: str = "", keyword: str = "") -> bool:
        return (
            cls._in_test(filename)
            | cls._is_blank(line)
            | cls._in_comment(line, file_ext, keyword)
            | cls._is_single_bracket(line)
        )

    @classmethod
    def file(cls, filename: str, file_ext: str) -> bool:
        return cls._in_test(filename) | bool(file_ext in cls._re_lang_comment.keys())

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
