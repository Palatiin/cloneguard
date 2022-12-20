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

    # TODO szz for code additions
    # TODO filter comment lines
    RECURSION = 3

    IGNORED_EXTENSIONS = [".txt", ".md", ".pdf"]

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
    def get_first_from_generator(gen: Generator) -> Any:
        try:
            val = next(gen)
            del gen
        except StopIteration:
            return [None]

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
            if filename.split(".")[-1] in self.IGNORED_EXTENSIONS:
                continue
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
                _lines_graph = self._process_equal_modification(
                    a_line, a_len, b_line, b_len, commit, prev_commit_blame, filename
                )
                _lines_graph = [self.annotate_line_recursive(node, filename) for node in _lines_graph]
            # addition
            elif a_len == 0:
                _lines_graph = self._process_addition(a_line, b_line, b_len, commit, filename)
            # deletion
            elif b_len == 0:
                _lines_graph = self._process_deletion(a_line, a_len, b_line, commit, prev_commit_blame, filename)
                _lines_graph = [self.annotate_line_recursive(node, filename) for node in _lines_graph]
            # unequal modification
            else:
                _lines_graph = self._process_unequal_modification(
                    a_line, a_len, b_line, b_len, commit, prev_commit_blame, filename
                )
                _lines_graph = [self.annotate_line_recursive(node, filename) for node in _lines_graph]
            annotated_lines.extend(_lines_graph)
        return annotated_lines

    def annotate_line_recursive(self, node: Node, filename: str) -> Node:
        if len(node.commits) > self.RECURSION or node.type_of_change[-1] == "A":
            return node

        prev_commit = self.get_first_from_generator(
            self.repo.rev_list(commit_id=node.commits[-1] + "~1", file=filename)
        )[0]
        if prev_commit is None:
            return node

        commit_diff = self.repo.diff(prev_commit, node.commits[-1])
        commit_diff = GitParser.parse_diff(commit_diff)[filename]
        diff_block = [
            diff
            for diff in commit_diff["affected_lines"]
            if diff["b"][0] <= node.line_mapping[-1] < diff["b"][0] + (diff["b"][1] or 1)
        ]

        prev_commit_blame = self.repo.annotate(prev_commit, filename)
        prev_commit_blame = GitParser.parse_annotation(prev_commit_blame)

        if len(diff_block) != 1:
            logger.warning(
                f"szz: annotate_line_recursive: Unexpected state - matching diff block count is {len(diff_block)}."
            )

        diff_block = diff_block[0]
        a_line, a_len = diff_block["a"]
        b_line, b_len = diff_block["b"]
        commit_type = "E" if a_len == b_len else "A" if a_len == 0 else "D" if b_len == 0 else "U"
        line_mapping = a_line + (node.line_mapping[-1] - b_line)
        line_mapping += a_len - 1 if a_len else 0
        if commit_type in ["E", "D"]:
            node.commits.append(prev_commit_blame[line_mapping - 1][0])
            node.line_mapping.append(line_mapping)
            node.type_of_change.append(commit_type)
        elif commit_type == "A":
            node.commits.append(prev_commit)
            node.line_mapping.append(a_line)
            node.type_of_change.append(commit_type)
        elif commit_type == "D":
            logger.warning("szz: annotate_line_recursive: nonsense - deletion")
        elif a_line <= line_mapping < a_line + (a_len or 1):
            node.commits.append(prev_commit_blame[line_mapping - 1][0])
            node.line_mapping.append(line_mapping)
            node.type_of_change.append(commit_type)
        else:
            logger.warning("szz: annotate_line_recursive: nonsense - deletion in unequal modification")

        return self.annotate_line_recursive(node, filename)

    def _process_addition(self, a_line: int, b_line: int, b_len: None | int, commit: str, filename: str) -> List[Node]:
        annotated = []
        prev_commit = self.get_first_from_generator(self.repo.rev_list(commit + "~1", filename))[0]
        for num in range(b_line, b_line + b_len):
            annotated.append(Node([num, a_line], [commit, prev_commit], ["A"]))
        return annotated

    def _process_deletion(
        self, a_line: int, a_len: None | int, b_line: int, commit: str, blame: List, filename: str
    ) -> List[Node]:
        annotated = []
        prev_commit = self.get_first_from_generator(self.repo.rev_list(commit + "~1", filename))[0]
        for num in range(a_line, a_line + a_len):
            prev_prev_commit = blame[num - 1][0]
            line_mapping = self._get_line_mapping(prev_prev_commit, prev_commit, filename, num)

            annotated.append(Node([b_line, line_mapping], [commit, prev_prev_commit], ["D"]))
        return annotated

    def _process_equal_modification(
        self, a_line: int, a_len: int, b_line: int, b_len: int, commit: str, blame: List, filename: str
    ) -> List[Node]:
        annotated = []
        for a_num, b_num in zip(range(a_line, a_line + a_len), range(b_line, b_line + b_len)):
            prev_commit = blame[a_num - 1][0]
            line_mapping = self._get_line_mapping(prev_commit, commit, filename, b_num)

            annotated.append(Node([b_num, line_mapping], [commit, prev_commit], ["E"]))
        return annotated

    def _process_unequal_modification(
        self, a_line: int, a_len: None | int, b_line: int, b_len: None | int, commit: str, blame: List, filename: str
    ) -> List[Node]:
        a_len = a_len or 0
        b_len = b_len or 0
        annotated = []
        blame_lines_of_code = len(blame)

        if a_len > b_len:
            b_num = b_line
            for a_num in range(a_line, a_line + a_len):
                prev_commit = blame[a_num - 1][0]
                if b_num <= blame_lines_of_code and b_num <= b_line + b_len:
                    line_mapping = self._get_line_mapping(prev_commit, commit, filename, b_num)

                    annotated.append(Node([b_num, line_mapping], [commit, prev_commit], ["U"]))
                    b_num += 1
                else:
                    prev_prev_commit = blame[a_num - 1][0]
                    line_mapping = self._get_line_mapping(prev_prev_commit, prev_commit, filename, a_num)

                    annotated.append(Node([b_line, line_mapping], [commit, prev_prev_commit], ["D"]))
            return annotated

        a_num = a_line
        prev_commit = self.get_first_from_generator(self.repo.rev_list(commit + "~1", filename))[0]
        for b_num in range(b_line, b_line + b_len):
            if a_num <= a_line + a_len:
                prev_commit_ = blame[a_num - 1][0]
                line_mapping = self._get_line_mapping(prev_commit_, commit, filename, b_num)

                annotated.append(Node([b_num, line_mapping], [commit, prev_commit_], ["U"]))
                a_num += 1
            else:
                annotated.append(Node([b_num, a_num], [commit, prev_commit], ["A"]))
        return annotated

    def _get_line_mapping(self, prev_commit: str, commit: str, filename: str, b_line_num: int) -> int:
        diff = GitParser.parse_diff(self.repo.diff(prev_commit, commit, path=filename))[filename]["affected_lines"]
        for lines in diff:
            b_line, b_len = lines["b"]
            if not (b_line <= b_line_num < b_line + (b_len or 1)):
                continue
            return lines["a"][0] + b_line_num - b_line

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
