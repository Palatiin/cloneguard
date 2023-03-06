# searcher.py

import re
from dataclasses import dataclass, field
from typing import List, Tuple

import nltk

from coinwatch.clients import Git
from coinwatch.settings import CONTEXT_LINES
from coinwatch.src.context_extractor import Context


@dataclass
class Sentence:
    filename: str
    file_extension: str
    line_number: int
    sentence: str


@dataclass
class TargetContext:
    key_statements: Tuple[Sentence, Sentence]
    boundary: List[Tuple[Tuple[int, int], Tuple[int, int]]]
    upper_code: List[Tuple[int, str]] = field(default_factory=list)
    lower_code: List[Tuple[int, str]] = field(default_factory=list)


class Searcher:
    _levenshtein_threshold = 0.25
    _re_lang_comment = {
        "py": r'\s*(#|""").*?{}',
        "c": r"\s*(/\*|//|/\*\*).*?{}",
        "cpp": r"\s*(/\*|//|/\*\*).*?{}",
    }

    def __init__(self, context: Tuple[Context, Context], target_repo: Git):
        self.context = context
        self.repo = target_repo

    @staticmethod
    def _get_similarity(string_a: str, string_b: str) -> float:
        """Normalize Levenshtein's distance metric."""
        return nltk.edit_distance(string_a, string_b) / len(max([string_a, string_b], key=len))

    @staticmethod
    def _in_test(filename: str) -> bool:
        return "test" in filename

    def _in_comment(self, file_extension: str, line: str, keyword: str) -> bool:
        """Check whether the occurrence of the keyword is in comment."""
        if re.search(self._re_lang_comment[file_extension].format(keyword), line, flags=re.S):
            return True
        return False

    def find_occurrences(self, keyword: str, key_sentence: str) -> List[Tuple[Sentence, float]]:
        """Find occurrence of context keywords in target repository."""
        occurrences = []
        grep_output = self.repo.grep(keyword.replace(".", "\\."))
        for line in grep_output:
            if not line:
                continue
            file, line_number, sentence = line.split(":", 2)
            sentence = sentence.strip()
            file_extension = file.split(".")[-1]
            if self._in_test(file):
                continue  # filter test files
            if file_extension not in self._re_lang_comment.keys():
                continue  # filter non-source code file extensions
            if self._in_comment(file_extension, sentence, keyword):
                continue  # filter occurrences in comments
            if (sim := self._get_similarity(sentence, key_sentence)) > self._levenshtein_threshold:
                continue  # filter based on similarity
            # TODO filter based on sentence type
            sentence = Sentence(file, file_extension, int(line_number), sentence)
            occurrences.append((sentence, sim))
        return occurrences

    @staticmethod
    def make_candidate_context_ks_pairs(
        upper_ksi: int, lower_ksi: int, occurrences: List[List[List[Tuple[Sentence, float]]]]
    ) -> List[Tuple[Sentence, Sentence]]:
        """Write something."""
        if upper_ksi < 0 or lower_ksi < 0:
            return []

        ks_pairs: List[Tuple[Sentence, Sentence]] = []
        for upper_occurrence, _ in occurrences[0][upper_ksi]:
            for lower_occurrence, _ in occurrences[1][lower_ksi]:
                if (
                    upper_occurrence.filename == lower_occurrence.filename
                    and upper_occurrence.line_number < lower_occurrence.line_number - 1
                ):
                    ks_pairs.append((upper_occurrence, lower_occurrence))

        return ks_pairs

    def get_line_range(self, ks_i: int, occurrence: Sentence) -> List[Tuple[int, str]]:
        """Get context of matched key statement."""
        file_lines = self.repo.open_file(occurrence.filename)
        line_range = []

        # context before key statement
        curr_lnum = occurrence.line_number - 1
        for line in file_lines[curr_lnum - 1 :: -1]:
            curr_lnum -= 1
            if len(line_range) == ks_i:  # noqa - duplicate code
                break
            line = line.strip()
            if not line:
                continue  # filter blank lines
            if re.match(self._re_lang_comment[occurrence.file_extension].format(""), line):
                continue  # filter comment lines
            line_range.append((curr_lnum, line))

        # key statement
        line_range.append((occurrence.line_number - 1, file_lines[occurrence.line_number - 1].strip()))

        # context after key statement
        curr_lnum = occurrence.line_number - 1
        for line in file_lines[curr_lnum + 1 :]:
            curr_lnum += 1
            if len(line_range) == CONTEXT_LINES:  # noqa
                break
            line = line.strip()
            if not line:
                continue  # filter blank lines
            if re.match(self._re_lang_comment[occurrence.file_extension].format(""), line):
                continue  # filter comment lines
            line_range.append((curr_lnum, line))

        return sorted(line_range, key=lambda x: x[0])

    def determine_boundary(
        self, kwi: int, ctx: int, target_code: List[Tuple[int, str]]
    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Determine boundary of candidate context - the start and end statement.

        Args:
            kwi (int): keyword index
            ctx (int): context index (0 - upper, 1 - lower)
            target_code (List[Tuple[int, str]]): surrounding lines of key statement in target code
        """

        def determine_start() -> Tuple[int, int]:
            for i in range(kwi + 1):  # end matching key statement index
                sim_list = []
                patch_context_statement: str = self.context[ctx].sentence_keyword_pairs[i][0]
                for j in range(len(target_code)):
                    sim = self._get_similarity(target_code[j][1], patch_context_statement)
                    sim_list.append(sim)
                start_statement_idx, value = min(enumerate(sim_list), key=lambda x: x[1])
                if value <= self._levenshtein_threshold:
                    return i, start_statement_idx
            return -1, -1

        def determine_end() -> Tuple[int, int]:
            for i in range(len(self.context[ctx].sentence_keyword_pairs) - 1, kwi - 1, -1):
                sim_list = []
                patch_context_statement: str = self.context[ctx].sentence_keyword_pairs[i][0]
                for j in range(len(target_code) - 1, -1, -1):
                    sim = self._get_similarity(target_code[j][1], patch_context_statement)
                    sim_list.append(sim)
                end_statement_idx, value = min(enumerate(sim_list), key=lambda x: x[1])
                if value <= self._levenshtein_threshold:
                    return i, len(target_code) - 1 - end_statement_idx
            return -1, -1

        return determine_start(), determine_end()

    def search(self):
        """Write something."""
        context_kw_occurrences: List[List[List[Tuple[Sentence, float]]]] = [[], []]
        key_statement_pos = [[-1, -1, 1.0], [-1, -1, 1.0]]

        # find key statements
        for i, context in enumerate(self.context):
            for j, sentence_keyword_pair in enumerate(context.sentence_keyword_pairs):
                sentence, keyword = sentence_keyword_pair
                occurrences = self.find_occurrences(keyword, sentence.strip())
                if not occurrences:
                    context_kw_occurrences[i].append([])
                    continue
                occurrence: Tuple
                max_similarity_index, occurrence = min(enumerate(occurrences), key=lambda x: x[1][1])
                if occurrence[1] < key_statement_pos[i][2]:
                    key_statement_pos[i] = [j, max_similarity_index, occurrence[1]]
                elif occurrence[1] == key_statement_pos[i][2] and len(keyword) > len(
                    context.sentence_keyword_pairs[key_statement_pos[i][0]][1]
                ):
                    key_statement_pos[i] = [j, max_similarity_index, occurrence[1]]
                context_kw_occurrences[i].append(occurrences)

        upper_ksi: int = key_statement_pos[0][0]
        lower_ksi: int = key_statement_pos[1][0]
        candidate_context_ks_pairs = self.make_candidate_context_ks_pairs(upper_ksi, lower_ksi, context_kw_occurrences)

        # create list of candidate contexts
        candidate_context_list: List[TargetContext] = []

        for upper_candidate_ks, lower_candidate_ks in candidate_context_ks_pairs:
            upper_target_context_code = self.get_line_range(upper_ksi, upper_candidate_ks)
            upper_boundary = self.determine_boundary(upper_ksi, 0, upper_target_context_code)

            lower_target_context_code = self.get_line_range(lower_ksi, lower_candidate_ks)
            lower_boundary = self.determine_boundary(lower_ksi, 1, lower_target_context_code)

            if (-1, -1) in upper_boundary or (-1, -1) in lower_boundary:
                continue
            if (
                upper_boundary[0][0] > upper_boundary[1][0]
                or upper_boundary[0][1] > upper_boundary[1][1]
                or lower_boundary[0][0] > lower_boundary[1][0]
                or lower_boundary[0][1] > lower_boundary[1][1]
            ):
                continue

            candidate_context_list.append(
                (
                    TargetContext(
                        key_statements=(upper_candidate_ks, lower_candidate_ks),
                        boundary=[upper_boundary, lower_boundary],
                        upper_code=upper_target_context_code,
                        lower_code=lower_target_context_code,
                    )
                )
            )

        # TODO: implement comparator and use it here to compare contexts
