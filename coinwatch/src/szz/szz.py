# szz.py

from dataclasses import dataclass
from datetime import datetime as dt
from typing import Any, Dict, Generator, List

from coinwatch.clients import Git
from coinwatch.settings import logger
from coinwatch.src.szz.git_parser import GitParser


@dataclass
class Node:
    line_mapping: List[int]
    commits: List[str]
    type_of_change: List[str]


class SZZ:
    """SZZ is an algorithm used for finding bug introducing commits in VCS."""

    RECURSION = 1

    def __init__(self, repo: Git, commits: List[str]):
        self.repo = repo
        self.commits = commits
        self.bug_time = None
        self.fix_time = None
        # TODO prepare multiprocessing

    def run(self) -> List[List[str | List[Any]]]:
        logger.info("Running SZZ algorithm.")

        annotated_files = {}
        for commit in self.commits:
            prev_commit = self.get_first_from_generator(self.repo.rev_list(commit_id=commit + "~1"))[0]
            commit_diff = self.repo.diff(prev_commit, commit)
            commit_diff = GitParser.parse_diff(commit_diff)
            annotated_files[commit] = self.annotate_files(commit, commit_diff)
        logger.info("SZZ annotation done.")

        fix_bug_commit_pairs = self.get_pairs(annotated_files)
        logger.info("SZZ done.")

        return fix_bug_commit_pairs

    @staticmethod
    def get_first_from_generator(gen: Generator):
        val = next(gen)
        del gen
        return val

    def annotate_files(self, commit: str, commit_diff: dict) -> Dict[str, List[Node]]:
        """Get fix-bug pairs for each file changed by commit.

        Args:
            commit (str): fixing commit
            commit_diff (dict): diff of fixing commit

        Returns:
            Dictionary, list of versions affecting each line in each file affected.
        """
        annotated_files: Dict[str, List[Node]] = {}
        for filename in commit_diff["affected_files"]:
            file_diff = commit_diff[filename]
            annotated_files[filename] = self.annotate_lines(commit, filename, file_diff)

        return annotated_files

    def annotate_lines(self, commit: str, filename: str, file_diff: dict) -> List[Node]:
        prev_commit_blame = self.get_first_from_generator(self.repo.rev_list(commit_id=commit + "~1", file=filename))[0]
        prev_commit_blame = self.repo.annotate(prev_commit_blame, filename)
        prev_commit_blame = GitParser.parse_annotation(prev_commit_blame)

        annotated_lines: List[Node] = []
        for diff in file_diff["affected_lines"]:
            """There are 4 possible scenarios:
            1. Equal Modification
            2. Addition
            3. Deletion
            4. Unequal Modification
            """
            a_line, a_len = diff["a"]
            b_line, b_len = diff["b"]

            # equal modification
            if a_len == b_len:
                a_len, b_len = a_len or 1, b_len or 1
                annotated_lines.extend(
                    self._process_equal_modification(a_line, a_len, b_line, b_len, commit, prev_commit_blame)
                )
            # addition
            elif a_len == 0:
                annotated_lines.extend(self._process_addition(b_line, b_len, commit))
            # deletion
            elif b_len == 0:
                annotated_lines.extend(self._process_deletion(a_line, a_len, b_line, commit, prev_commit_blame))
            # unequal modification
            else:
                annotated_lines.extend(
                    self._process_unequal_modification(a_line, a_len, b_line, b_len, commit, prev_commit_blame)
                )
        return annotated_lines

    @staticmethod
    def _process_addition(b_line: int, b_len: None | int, commit: str) -> List[Node]:
        annotated = []
        for num in range(b_line, b_line + b_len):
            annotated.append(Node([num], [commit], ["A"]))
        return annotated

    def _process_deletion(self, a_line: int, a_len: None | int, b_line: int, commit: str, blame: List) -> List[Node]:
        annotated = []
        for num in range(a_line, a_line + a_len):
            blamed_line = blame[num - 1]
            commit_date = dt.strptime(blamed_line[2], "%Y-%m-%d %H:%M:%S %z")
            self.bug_time = commit_date if not self.bug_time or commit_date < self.bug_time else self.bug_time
            annotated.append(Node([b_line, num], [commit, blamed_line[0]], ["D"]))
        return annotated

    def _process_equal_modification(
        self, a_line: int, a_len: int, b_line: int, b_len: int, commit: str, blame: List
    ) -> List[Node]:
        annotated = []
        for a_num, b_num in zip(range(a_line, a_line + a_len), range(b_line, b_line + b_len)):
            blamed_line = blame[a_num - 1]
            commit_date = dt.strptime(blamed_line[2], "%Y-%m-%d %H:%M:%S %z")
            self.bug_time = commit_date if not self.bug_time or commit_date < self.bug_time else self.bug_time
            annotated.append(Node([b_num, a_num], [commit, blamed_line[0]], ["E"]))
        return annotated

    def _process_unequal_modification(
        self, a_line: int, a_len: None | int, b_line: int, b_len: None | int, commit: str, blame: List
    ) -> List[Node]:
        a_len = a_len or 0
        b_len = b_len or 0
        annotated = []
        blame_lines_of_code = len(blame)

        if a_len > b_len:
            b_num = b_line
            for a_num in range(a_line, a_line + a_len):
                blamed_line = blame[a_num - 1]
                commit_date = dt.strptime(blamed_line[2], "%Y-%m-%d %H:%M:%S %z")
                self.bug_time = commit_date if not self.bug_time or commit_date < self.bug_time else self.bug_time
                if b_num <= blame_lines_of_code and b_num < b_line + b_len:
                    annotated.append(Node([b_num, a_num], [commit, blamed_line[0]], ["U"]))
                    b_num += 1
                else:
                    annotated.append(Node([b_num, a_num], [commit, blamed_line[0]], ["D"]))
            return annotated

        a_num = a_line
        for b_num in range(b_line, b_line + b_len):
            blamed_line = blame[a_num - 1]
            commit_date = dt.strptime(blamed_line[2], "%Y-%m-%d %H:%M:%S %z")
            self.bug_time = commit_date if not self.bug_time or commit_date < self.bug_time else self.bug_time
            if a_num < a_line + a_len:
                annotated.append(Node([b_num, a_num], [commit, blamed_line[0]], ["U"]))
                a_num += 1
            else:
                annotated.append(Node([b_num], [commit], ["A"]))
        return annotated

    def get_pairs(self, candidates: Dict[str, Dict]) -> List[List[str | List[Any]]]:
        pairs = []
        for key in candidates:
            pair = [key, []]
            for i in range(1, self.RECURSION + 1):  # on 0th index is fix commit
                pair[1].append(
                    [
                        node.commits[i]
                        for file in candidates[key]
                        for node in candidates[key][file]
                        if len(node.commits) > i
                    ]
                )
            pairs.append(pair)
        return pairs
