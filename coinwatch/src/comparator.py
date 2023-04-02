# comparator.py

from enum import Enum
from typing import List

import structlog
from similarity.normalized_levenshtein import NormalizedLevenshtein  # noqa

from coinwatch.settings import REWARD, THRESHOLD
from coinwatch.src.patch_fetcher import PatchCode, PatchType

logger = structlog.get_logger()


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
        p: float = float(len(source) if len(source) > len(target) else len(target))

        similarity_sum: float = 0.0
        for i, source_code in enumerate(source):
            similarities: List[float] = []
            for target_code in target:
                similarities.append(cls.similarity(source_code, target_code))
            most_similar_index, value = max(enumerate(similarities), key=lambda x: x[1])
            similarity_sum += value * cls._reward ** (abs(i - most_similar_index))

        return similarity_sum / p

    @classmethod
    def determine_patch_application(cls, patch: PatchCode, target: List[str]):
        assert patch.type != PatchType.NDF, "Patch type is not defined."

        if patch.type == PatchType.DEL:
            if (sim := cls.compare(target, patch.sanitize())) >= cls._threshold:
                return False, sim
            return True, sim
        elif patch.type == PatchType.ADD:
            if (sim := cls.compare(target, patch.sanitize())) >= cls._threshold:
                return True, sim
            return False, sim
        elif patch.type == PatchType.CHG:
            add_sim = 0.0
            if (del_sim := cls.compare(target, patch.sanitize(True))) >= cls._threshold and (
                add_sim := cls.compare(target, patch.sanitize())
            ) >= cls._threshold:
                sim = del_sim + add_sim
                if del_sim >= add_sim:
                    return False, sim
                return True, sim
            return None, del_sim + add_sim
