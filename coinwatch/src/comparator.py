# comparator.py

from enum import Enum
from typing import List

from nltk import edit_distance

from coinwatch.settings import REWARD


class TypeOfPatch(int, Enum):
    DEL: int = 0
    ADD: int = 1
    CHA: int = 2


class Comparator:
    _reward: float = REWARD

    @staticmethod
    def _get_similarity(string_a: str, string_b: str) -> float:
        """Normalize Levenshtein's distance metric."""
        return edit_distance(string_a, string_b) / len(max([string_a, string_b], key=len))

    def compare(self, source: List[str], target: List[str]) -> float:
        p: float = float(len(source))

        similarity_sum: float = 0.0
        for i, source_code in enumerate(source):
            similarities: List[float] = []
            for target_code in target:
                similarities.append(self._get_similarity(source_code, target_code))
            most_similar_index, value = min(enumerate(similarities), key=lambda x: x[1])
            similarity_sum += value * self._reward ** (abs(i - most_similar_index))

        return similarity_sum / p
