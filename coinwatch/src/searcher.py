# searcher.py

import re
from typing import List, Tuple

import nltk

from coinwatch.clients import Git
from coinwatch.settings import CONTEXT_LINES
from coinwatch.src.context_extractor import Context


class Searcher:
    _levenshtein_threshold = 0.25
    _re_lang_comment = {
        "py": r'(?:#|""").*?{}',
        "c": r"(?:/*|//|/**).*?{}",
        "cpp": r"(?:/*|//|/**).*?{}",
    }

    def __init__(self, context: Tuple[Context, Context], target_repo: Git):
        self.context = context
        self.repo = target_repo

    @staticmethod
    def _get_similarity(string_a: str, string_b: str) -> float:
        """Normalize Levenshtein's distance metric."""
        return nltk.edit_distance(string_a, string_b) / len(max([string_a, string_b], key=len))

    def _in_comment(self, file_extension: str, line: str, keyword: str) -> bool:
        """Check whether the occurrence of the keyword is in comment."""
        if re.search(self._re_lang_comment[file_extension].format(keyword), line):
            return True
        return False

    def find_occurrences(self, keyword: str, key_sentence: str) -> List[Tuple[str, float]]:
        """Find occurrence of context keywords in target repository."""
        occurrences = []
        grep_output = self.repo.grep(keyword.replace(".", "\\."))
        for line in grep_output:
            file, _, sentence = line.split(":", 2)
            sentence = sentence.strip()
            file_extension = file.split(".")[-1]
            if "test" in file:
                continue  # filter test files
            if file_extension not in self._re_lang_comment.keys():
                continue  # filter non-source code file extensions
            if self._in_comment(file_extension, sentence, keyword):
                continue  # filter occurrences in comments
            if (sim := self._get_similarity(sentence, key_sentence)) > self._levenshtein_threshold:
                continue  # filter based on similarity
            # TODO filter based on sentence type
            occurrences.append((line, sim))
        return occurrences

    def get_line_range(self, ks_i: int, occurrence: str) -> List[str]:
        """Get context of matched key statement."""
        file, line_number, sentence = occurrence[0].split(":", 2)
        return self.repo.get_lines(file, line_number - ks_i, line_number + ks_i - CONTEXT_LINES)

    def search(self):
        context_kw_occurrences = [[], []]
        key_statement_pos = [[None, None, 1.0], [None, None, 1.0]]

        # find key statements
        for i, context in enumerate(self.context):
            for j, sentence_keyword_pair in enumerate(context.sentence_keyword_pairs):
                sentence, keyword = sentence_keyword_pair
                occurrences = self.find_occurrences(keyword, sentence.strip())
                max_similarity_index, value = min(enumerate(occurrences), key=lambda x: x[1])
                if value < key_statement_pos[i][2]:
                    key_statement_pos[i] = [j, max_similarity_index, value]
                context_kw_occurrences[i].append(occurrences)
