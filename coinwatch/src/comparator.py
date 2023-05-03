# comparator.py
import multiprocessing
from enum import Enum
from typing import List

from similarity.normalized_levenshtein import NormalizedLevenshtein  # noqa

from coinwatch.settings import REWARD, THRESHOLD
from coinwatch.src.patch_fetcher import PatchCode, PatchType
from coinwatch.src.schemas import CandidateCode


class TypeOfPatch(int, Enum):
    DEL: int = 0
    ADD: int = 1
    CHA: int = 2


class Comparator:
    _threshold: float = THRESHOLD
    _reward: float = REWARD
    levenshtein = NormalizedLevenshtein()

    @classmethod
    def similarity(cls, string_a: str, string_b: str) -> float:
        """Normalize Levenshtein's edit distance metric."""
        return cls.levenshtein.similarity(string_a, string_b)

    @classmethod
    def compare(cls, source: List[str], target: List[str]) -> float:
        p: float = float(len(source))

        similarity_sum: float = 0.0
        with multiprocessing.Pool() as pool:
            similarities = pool.starmap(
                cls.similarity, [(source_code, target_code) for source_code in source for target_code in target]
            )
            similarities = [similarities[i : i + len(target)] for i in range(0, len(similarities), len(target))]
            for i, source_code in enumerate(source):
                most_similar_index, value = max(enumerate(similarities[i]), key=lambda x: x[1])
                similarity_sum += value * cls._reward ** (abs(i - most_similar_index))

        return similarity_sum / p

    @classmethod
    def determine_patch_application(cls, patch: PatchCode, target: CandidateCode):
        assert patch.type != PatchType.NDF, "Patch type is not defined."

        if patch.type == PatchType.DEL:
            if not len(target.code):  # prevent ZeroDivisionError in compare method
                return True, target.context.similarity
            if (sim := cls.compare(target.code, patch.sanitize())) >= cls._threshold:
                return False, sim
            return True, sim
        elif patch.type == PatchType.ADD:
            if not len(target.code):  # prevent ZeroDivisionError in compare method
                return False, target.context.similarity
            if (sim := cls.compare(target.code, patch.sanitize())) >= cls._threshold:
                return True, sim
            return False, sim
        elif patch.type == PatchType.CHG:
            add_sim = 0.0
            if not len(target.code):
                return None, 0.0
            if (del_sim := cls.compare(target.code, patch.sanitize(True))) >= cls._threshold and (
                add_sim := cls.compare(target.code, patch.sanitize())
            ) >= cls._threshold:
                sim = del_sim + add_sim
                if del_sim >= add_sim:
                    return False, sim
                return True, sim
            return None, del_sim + add_sim
