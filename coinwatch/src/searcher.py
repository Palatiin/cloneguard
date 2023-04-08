# searcher.py

import multiprocessing
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import structlog

from coinwatch.clients.git import Git
from coinwatch.settings import CONTEXT_LINES
from coinwatch.src.common import Filter, log_wrapper
from coinwatch.src.comparator import Comparator
from coinwatch.src.context_extractor import Context
from coinwatch.src.schemas import CandidateCode, Sentence, TargetContext

logger = structlog.get_logger(__name__)


class Searcher:
    _levenshtein_threshold = 0.25

    def __init__(self, context: Tuple[Context, Context], target_repo: Git):
        self.context = context
        self.upper_context_lines = [pair[0] for pair in self.context[0].sentence_keyword_pairs]
        self.lower_context_lines = [pair[0] for pair in self.context[1].sentence_keyword_pairs]
        self.repo = target_repo

    @staticmethod
    def process_line(line, keyword, key_sentence, levenshtein_threshold):
        try:
            file, line_number, sentence = line.split(":", 2)
        except Exception as e:
            print(str(e))
            return None
        sentence = sentence.strip()
        file_extension = Path(file).suffix[1:]
        if Filter.file(filename=file, file_ext=file_extension):
            return None
        if Filter.line(sentence, filename=file, file_ext=file_extension, keyword=keyword):
            return None
        sim = Comparator.similarity(sentence, key_sentence)
        if sim <= levenshtein_threshold:
            return None
        # TODO filter based on sentence type
        sentence = Sentence(file, file_extension, int(line_number), sentence)
        return sentence, sim

    def find_occurrences(self, keyword: str, key_sentence: str) -> List[Tuple[Sentence, float]]:
        """Find occurrence of context keywords in target repository."""
        occurrences = []
        grep_output = self.repo.grep(re.escape(keyword), files=f"**/*.{self.repo.language}")

        with multiprocessing.Pool() as pool:
            results = pool.starmap(
                self.process_line, [(line, keyword, key_sentence, self._levenshtein_threshold) for line in grep_output]
            )
            occurrences = [result for result in results if result is not None]

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

        Return:
            Pairs of mapped context index boundaries - patch ctx start statement : candidate start statement
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

        if (upper_sim := Comparator.compare(upper_pctx, upper_cctx)) > self._levenshtein_threshold and (
            lower_sim := Comparator.compare(lower_pctx, lower_cctx)
        ) > self._levenshtein_threshold:
            candidate_context.similarity = upper_sim + lower_sim
            return True
        return False

    def _get_candidate_code_list(self, candidates: List[TargetContext], patch_lenght: int) -> List[CandidateCode]:
        candidate_code_list: List[CandidateCode] = []

        for candidate in candidates:
            filename = candidate.key_statements[0].filename
            file_ext = Path(filename).suffix[1:]
            file = self.repo.open_file(filename)
            start_line = candidate.upper_code[candidate.boundary[0][1][1]][0] + 1
            end_line = candidate.lower_code[candidate.boundary[1][0][1]][0]
            candidate_code: List[str] = []
            line_count: int = 0
            for line in file[start_line:end_line]:
                line = line.strip()
                if Filter.line(line, filename, file_ext):
                    continue
                line_count += 1
                if line_count > patch_lenght * 5:
                    break
                candidate_code.append(line)
            if line_count < patch_lenght * 5:
                candidate_code_list.append(
                    CandidateCode(
                        context=candidate,
                        code=candidate_code,
                    )
                )

        return candidate_code_list

    @log_wrapper
    def search(self, patch_length: int) -> List[CandidateCode]:
        """Find and return candidate codes in target repository."""
        context_kw_occurrences: List[List[List[Tuple[Sentence, float]]]] = [[], []]
        key_statement_pos = [[-1, -1, 0], [-1, -1, 0]]

        # find key statements
        logger.info("searcher: search: start finding KS")
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
        logger.info("searcher: search: KS found")

        upper_ksi: int = key_statement_pos[0][0]
        lower_ksi: int = key_statement_pos[1][0]
        candidate_context_ks_pairs = self.make_candidate_context_ks_pairs(upper_ksi, lower_ksi, context_kw_occurrences)

        # create list of candidate contexts
        candidate_context_list: List[TargetContext] = []

        for upper_candidate_ks, lower_candidate_ks in candidate_context_ks_pairs:
            upper_target_context_code = self.get_line_range(upper_ksi, upper_candidate_ks)
            upper_boundary = self.determine_boundary(upper_ksi, 0, upper_target_context_code)
            if (
                (-1, -1) in upper_boundary
                or upper_boundary[0][0] > upper_boundary[1][0]
                or upper_boundary[0][1] > upper_boundary[1][1]
            ):
                continue

            lower_target_context_code = self.get_line_range(lower_ksi, lower_candidate_ks)
            lower_boundary = self.determine_boundary(lower_ksi, 1, lower_target_context_code)
            if (
                (-1, -1) in lower_boundary
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

        return self._get_candidate_code_list(candidate_context_list, patch_length)
