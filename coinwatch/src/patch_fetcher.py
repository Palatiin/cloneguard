# patch_fetcher.py

import re
from enum import Enum
from typing import List


class PatchType(int, Enum):
    NDF = 0
    DEL = 1
    ADD = 2
    CHG = 3


class PatchCode:
    deletions: int = 0
    additions: int = 0
    type: PatchType = PatchType.NDF
    code: List[str] = []
    code_deletions: List[str] = []
    code_additions: List[str] = []

    _re_comment = re.compile(r"\s*(/\*|//|/\*\*).*?")

    def __init__(self, patch: List[str]):
        self.patch = patch

    def _filter(self, line: str) -> bool:
        if not line:
            return True
        if self._re_comment.match(line):
            return True
        return False

    def fetch(self):
        """Fetch code from patch."""
        additions, deletions = 0, 0
        for line in self.patch:
            line = line.strip()
            if line.startswith("-"):
                if self._filter(line):
                    continue
                deletions += 1
                self.code_deletions.append(line[1:].strip())
                self.code.append(line[1:].strip())
            elif line.startswith("+"):
                if self._filter(line):
                    continue
                additions += 1
                self.code_additions.append(line[1:].strip())
                self.code.append(line[1:].strip())

        patch_type: PatchType = PatchType.NDF
        if deletions and not additions:
            patch_type = PatchType.DEL
        elif not deletions and additions:
            patch_type = PatchType.ADD
        elif deletions and additions:
            patch_type = PatchType.CHG

        self.deletions = deletions
        self.additions = additions
        self.type = patch_type

        return self

    def sanitize(self, deletions=False):
        """Remove signs of addition or insertion and return pure code."""
        code = self.code
        if self.type == PatchType.CHG:
            code = self.code_deletions if deletions else self.code_additions
        sanitized: List[str] = []

        for line in code:
            if line.startswith("-") or line.startswith("+"):
                line = line[1:]
            sanitized.append(line.strip())

        return sanitized
