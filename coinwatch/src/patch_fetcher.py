# patch_fetcher.py

from enum import Enum
from typing import List

from coinwatch.src.common import Filter


class PatchType(int, Enum):
    NDF = 0
    DEL = 1
    ADD = 2
    CHG = 3


class PatchCode:
    def __init__(self, patch: str | List[str]):
        self.patch: List[str] = patch.splitlines() if isinstance(patch, str) else patch
        self.deletions: int = 0
        self.additions: int = 0
        self.type: PatchType = PatchType.NDF
        self.code: List[str] = []
        self.code_deletions: List[str] = []
        self.code_additions: List[str] = []

    def fetch(self):
        """Fetch code from patch."""
        additions, deletions = 0, 0
        for line in self.patch:
            line = line.strip()
            _line = line[1:].strip() if line.startswith("-") or line.startswith("+") else line
            if Filter.line(_line):
                continue
            if line.startswith("-"):
                deletions += 1
                self.code_deletions.append(line[1:].strip())
                self.code.append(line[1:].strip())
            elif line.startswith("+"):
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
