# git_parser.py

import re
from typing import List


class GitParser:
    _res = {
        "diff": {
            "files": re.compile(r"^diff\s--git\sa/(.*?)\sb/(.*?)$"),
            "lines": re.compile(r"^@@\s-(?P<start_a>\d+)(?P<len_a>,\d+)?\s\+(?P<start_b>\d+)(?P<len_b>,\d+)?\s@@"),
        }
    }

    @staticmethod
    def parse_annotation(annotate: List[str]) -> List[List[str]]:
        return [line.split("\t") for line in annotate]

    @classmethod
    def parse_diff(cls, diff: str) -> dict:
        """Parse output from Git client method diff.

        {
            "affected_files": [file_1, ...],
            "file_1": {
                "affected_lines": [
                    {
                        "a": (30, 0),
                        "b": (31, None),
                        "diff_lines": ['+print("Hello")', ...],
                    },
                    ...
                ]
            },
            ...
        }

        Args:
            diff (str): diff method

        Returns:
            Dictionary, parsed diff.
        """
        diff_lines = diff.split("\n")
        struct_diff = {"affected_files": []}
        file = None
        reading_diff_lines = False
        for line in diff_lines:
            if match := cls._res["diff"]["files"].search(line):
                reading_diff_lines = False
                file = match.group(2)
                struct_diff["affected_files"].append(file)
                struct_diff[file] = {}
                struct_diff[file]["affected_lines"] = []
            elif match := cls._res["diff"]["lines"].search(line):
                match = match.groupdict()
                # note: len_X: 0 == addition, None == changed only start_X line - no multiline
                len_a = int(match.get("len_a").strip(",")) if match.get("len_a") else None
                len_b = int(match.get("len_b").strip(",")) if match.get("len_b") else None
                struct_diff[file]["affected_lines"].append(
                    {
                        "a": (int(match["start_a"]), len_a),
                        "b": (int(match["start_b"]), len_b),
                        "diff_lines": [],
                    }
                )
                reading_diff_lines = True
            elif reading_diff_lines and line:
                struct_diff[file]["affected_lines"][-1]["diff_lines"].append(line)

        return struct_diff
