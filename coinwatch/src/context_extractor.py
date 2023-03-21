# context_extractor.py

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from coinwatch.src.common import Filter, log_wrapper


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
    def extract(self, patch: str) -> Tuple[Context, Context]:
        """Extract Upper and Lower patch context.

        Args:
            patch (str): source code from patch

        Returns:
            Tuple with Upper and Lower context - keywords representing leading and trailing code context.
        """
        patch_lines: List[str] = patch.split("\n")
        patch_lines = list(filter(lambda x: x, patch_lines))

        context: Tuple[Context, Context] = Context(), Context()

        is_lower = int(False)
        for line in patch_lines:
            line = line.strip()
            if not line or (len(line) == 1 and line[0] in ("+", "-")):
                # skip empty lines
                continue
            if line[0] in ("+", "-"):
                # skip patch lines
                is_lower = int(True)
                continue
            if Filter.line(line):
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
