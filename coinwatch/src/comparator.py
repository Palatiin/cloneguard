# comparator.py

from enum import Enum
from typing import List

from similarity.normalized_levenshtein import NormalizedLevenshtein

from coinwatch.settings import REWARD


class TypeOfPatch(int, Enum):
    DEL: int = 0
    ADD: int = 1
    CHA: int = 2


class Comparator:
    _reward: float = REWARD
    levenshtein = NormalizedLevenshtein()

    @classmethod
    def similarity(cls, string_a: str, string_b: str) -> float:
        """Normalize Levenshtein's distance metric."""
        return cls.levenshtein.similarity(string_a, string_b)

    @classmethod
    def compare(cls, source: List[str], target: List[str]) -> float:
        p: float = float(len(source))

        similarity_sum: float = 0.0
        for i, source_code in enumerate(source):
            similarities: List[float] = []
            for target_code in target:
                similarities.append(cls.similarity(source_code, target_code))
            most_similar_index, value = max(enumerate(similarities), key=lambda x: x[1])
            similarity_sum += value * cls._reward ** (abs(i - most_similar_index))

        return similarity_sum / p
