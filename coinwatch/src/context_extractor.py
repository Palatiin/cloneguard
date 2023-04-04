# context_extractor.py

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from coinwatch.clients.git import Git
from coinwatch.src.common import Filter, log_wrapper
from coinwatch.src.szz.git_parser import GitParser


@dataclass
class Context:
    """Data class representing context and its keywords."""

    is_eof: bool = False
    sentence_keyword_pairs: List[Tuple[str, str]] = field(default_factory=list)


class Extractor:
    """Extractor of patch context."""

    _re_token = re.compile(r"[a-zA-Z0-9!._]+")

    def __init__(self, context_lines: Optional[int] = 5):
        self.context_lines = context_lines

    def _tokenize(self, line: str) -> List[str]:
        """Tokenize line of code.

        Args:
            line (str): line of code

        Returns:
            Tokens from the line of code.
        """
        return self._re_token.findall(line)

    @log_wrapper
    def extract(self, patch: str | List[str]) -> Tuple[Context, Context]:
        """Extract Upper and Lower patch context.

        Args:
            patch (str): source code from patch

        Returns:
            Tuple with Upper and Lower context - keywords representing leading and trailing code context.
        """
        patch_lines: List[str] = patch.splitlines() if isinstance(patch, str) else patch
        context: Tuple[Context, Context] = Context(), Context()

        is_lower = int(False)
        for line in patch_lines:
            line = line.strip()
            if not line:
                continue
            if line[0] in ("+", "-"):
                # skip patch lines
                is_lower = int(True)
                continue
            _line = line[1:].strip() if line.startswith("-") or line.startswith("+") else line
            if Filter.line(_line):
                continue

            # tokenize context lines
            tokens = self._tokenize(line)
            # select the longest token as keyword
            keyword = max(tokens, key=len)
            context[is_lower].sentence_keyword_pairs.append((line, keyword))

        # check number of context keywords
        if (ctx_lines := len(context[0].sentence_keyword_pairs)) > self.context_lines:
            context[0].sentence_keyword_pairs = context[0].sentence_keyword_pairs[-self.context_lines :]
        elif ctx_lines < self.context_lines:
            context[0].is_eof = True

        if (ctx_lines := len(context[1].sentence_keyword_pairs)) > self.context_lines:
            context[1].sentence_keyword_pairs = context[1].sentence_keyword_pairs[: self.context_lines]
        elif ctx_lines < self.context_lines:
            context[1].is_eof = True

        return context

    @staticmethod
    def get_patch_from_commit(repo: Git, commit: str) -> List[List[str]]:
        diff = repo.show(commit, quiet=False, context=10)
        parsed_diff = GitParser().parse_diff(diff)

        relevant_files = [file for file in parsed_diff["affected_files"] if not Filter.file(filename=file)]
        patch_list = []
        for file in relevant_files:
            file_ext = Path(file).suffix[1:]
            for block in parsed_diff[file]["affected_lines"]:
                patch: List[str] = []
                for line in block["diff_lines"]:
                    line = line.strip()
                    _line = line[1:].strip() if line.startswith("-") or line.startswith("+") else line
                    if Filter.line(_line, filename=file, file_ext=file_ext):
                        continue
                    patch.append(line)
                patch_list.append(patch)

        return patch_list
