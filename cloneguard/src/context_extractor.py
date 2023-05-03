# File: src/context_extractor.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-02-13
# Description: Implementation of component Extractor.
# https://www.ndss-symposium.org/wp-content/uploads/2023/02/ndss2023_f222_paper.pdf

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from cloneguard.clients.git import Git
from cloneguard.src.common import Filter, log_wrapper
from cloneguard.src.errors import ContextExtractionError
from cloneguard.src.git_parser import GitParser


@dataclass
class Context:
    """Data class representing context and its keywords."""

    is_eof: bool = False
    sentence_keyword_pairs: List[Tuple[str, str]] = field(default_factory=list)


class Extractor:
    """Extractor of patch context."""

    _re_token = re.compile(r"[a-zA-Z0-9!._]+")

    def __init__(self, lang: str, context_lines: Optional[int] = 5):
        self.context_lines = context_lines
        self.language = lang

    def _tokenize(self, line: str) -> List[str]:
        """Tokenize line of code.

        Args:
            line (str): line of code

        Returns:
            Tokens from the line of code.
        """
        return self._re_token.findall(line)

    def _get_context(self, lines: List[str]) -> Context:
        """Get sentences and keywords representing the context.

        Raises ContextExtractionError if the lines do not contain additions/deletions.
        """
        # def get_keyword(line: str) -> str:
        #     tokens = sorted(self._tokenize(line))
        #     for token in tokens:
        #
        #     return tokens[0]
        context = Context()

        for line in lines:
            line = line.strip()
            if line.startswith("+") or line.startswith("-"):
                if Filter.line(line[1:].strip(), file_ext=self.language):
                    continue  # skip unnecessary patch lines
                break  # ==== reached patch code, end of the context ====
            elif Filter.line(line, file_ext=self.language):
                continue  # filter unimportant lines like comments

            # select keyword representing the sentence
            tokens = self._tokenize(line)
            keyword = max(tokens, key=len)
            context.sentence_keyword_pairs.append((line, keyword))
        else:  # went through all lines, but didn't find any editing
            raise ContextExtractionError("No additions/deletions in patch code.")

        return context

    @log_wrapper
    def extract(self, patch: str | List[str]) -> Tuple[Context, Context]:
        """Extract Upper and Lower patch context.

        Args:
            patch (str): source code from patch

        Returns:
            Tuple with Upper and Lower context - keywords representing leading and trailing code context.
        """
        patch_lines: List[str] = patch.splitlines() if isinstance(patch, str) else patch

        upper_context: Context = self._get_context(patch_lines)
        upper_context.sentence_keyword_pairs = upper_context.sentence_keyword_pairs[-self.context_lines :]
        upper_context.is_eof = False if len(upper_context.sentence_keyword_pairs) == self.context_lines else True

        lower_context: Context = self._get_context(patch_lines[::-1])
        lower_context.sentence_keyword_pairs = lower_context.sentence_keyword_pairs[-self.context_lines :][::-1]
        lower_context.is_eof = False if len(lower_context.sentence_keyword_pairs) == self.context_lines else True

        return upper_context, lower_context

    @staticmethod
    def get_patch_from_commit(repo: Git, commit: str, context: int = 10) -> List[List[str]]:
        diff = repo.show(commit, quiet=False, context=context)
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
