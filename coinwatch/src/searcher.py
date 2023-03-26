# searcher.py

from dataclasses import dataclass, field
from typing import List, Tuple

from coinwatch.clients.git import Git
from coinwatch.settings import CONTEXT_LINES
from coinwatch.src.common import Filter, log_wrapper
from coinwatch.src.comparator import Comparator
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

    def __init__(self, context: Tuple[Context, Context], target_repo: Git):
        self.context = context
        self.upper_context_lines = [pair[0] for pair in self.context[0].sentence_keyword_pairs]
        self.lower_context_lines = [pair[0] for pair in self.context[1].sentence_keyword_pairs]
        self.repo = target_repo

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
            if Filter.file(filename=file, file_ext=file_extension):
                continue
            if Filter.line(line, filename=file, file_ext=file_extension, keyword=keyword):
                continue
            if (sim := Comparator.similarity(sentence, key_sentence)) <= self._levenshtein_threshold:
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
            if len(line_range) == ks_i:
                break
            line = line.strip()
            if Filter.line(line):
                continue
            line_range.append((curr_lnum, line))

        # key statement
        line_range.append((occurrence.line_number - 1, file_lines[occurrence.line_number - 1].strip()))

        # context after key statement
        curr_lnum = occurrence.line_number - 1
        for line in file_lines[curr_lnum + 1 :]:
            curr_lnum += 1
            if len(line_range) == CONTEXT_LINES:
                break
            line = line.strip()
            if Filter.line(line):
                continue
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
                    sim = Comparator.similarity(target_code[j][1], patch_context_statement)
                    sim_list.append(sim)
                start_statement_idx, value = max(enumerate(sim_list), key=lambda x: x[1])
                if value > self._levenshtein_threshold:
                    return i, start_statement_idx
            return -1, -1

        def determine_end() -> Tuple[int, int]:
            for i in range(len(self.context[ctx].sentence_keyword_pairs) - 1, kwi - 1, -1):
                sim_list = []
                patch_context_statement: str = self.context[ctx].sentence_keyword_pairs[i][0]
                for j in range(len(target_code) - 1, -1, -1):
                    sim = Comparator.similarity(target_code[j][1], patch_context_statement)
                    sim_list.append(sim)
                end_statement_idx, value = max(enumerate(sim_list), key=lambda x: x[1])
                if value > self._levenshtein_threshold:
                    return i, len(target_code) - 1 - end_statement_idx
            return -1, -1

        return determine_start(), determine_end()

    def _check_candidate_context_similarity(self, candidate_context: TargetContext) -> bool:
        upper_boundary, lower_boundary = candidate_context.boundary
        upper_cctx = [line[1] for line in candidate_context.upper_code[upper_boundary[0][1] : upper_boundary[1][1] + 1]]
        lower_cctx = [line[1] for line in candidate_context.lower_code[lower_boundary[0][1] : lower_boundary[1][1] + 1]]

        upper_pctx = self.upper_context_lines[upper_boundary[0][0] : upper_boundary[1][0] + 1]
        lower_pctx = self.lower_context_lines[lower_boundary[0][0] : lower_boundary[1][0] + 1]

        if (
            Comparator.compare(upper_pctx, upper_cctx) > self._levenshtein_threshold
            and Comparator.compare(lower_pctx, lower_cctx) > self._levenshtein_threshold
        ):
            return True
        return False

    def _get_candidate_code_list(self, candidates: List[TargetContext]) -> List[List[str]]:
        candidate_code_list: List[List[str]] = []

        for candidate in candidates:
            file = self.repo.open_file(candidate.key_statements[0].filename)
            start_line = candidate.upper_code[candidate.boundary[0][1][1]][0] + 1
            end_line = candidate.lower_code[candidate.boundary[1][0][1]][0]
            candidate_code: List[str] = []
            for line in file[start_line:end_line]:
                line = line.strip()
                if Filter.line(line):
                    continue
                candidate_code.append(line)
            if candidate_code:
                candidate_code_list.append(candidate_code)

        return candidate_code_list

    @log_wrapper
    def search(self) -> List[List[str]]:
        """Find and return candidate codes in target repository."""
        context_kw_occurrences: List[List[List[Tuple[Sentence, float]]]] = [[], []]
        key_statement_pos = [[-1, -1, 0], [-1, -1, 0]]

        # find key statements
        for i, context in enumerate(self.context):
            for j, sentence_keyword_pair in enumerate(context.sentence_keyword_pairs):
                sentence, keyword = sentence_keyword_pair
                occurrences = self.find_occurrences(keyword, sentence.strip())
                if not occurrences:
                    context_kw_occurrences[i].append([])
                    continue
                occurrence: Tuple
                max_similarity_index, occurrence = max(enumerate(occurrences), key=lambda x: x[1][1])
                if occurrence[1] > key_statement_pos[i][2]:
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

            candidate_context = TargetContext(
                key_statements=(upper_candidate_ks, lower_candidate_ks),
                boundary=[upper_boundary, lower_boundary],
                upper_code=upper_target_context_code,
                lower_code=lower_target_context_code,
            )

            if not self._check_candidate_context_similarity(candidate_context):
                continue
            candidate_context_list.append(candidate_context)

        return self._get_candidate_code_list(candidate_context_list)
