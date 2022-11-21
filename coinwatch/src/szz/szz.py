# szz.py

from typing import Dict, Generator, List, Tuple

from coinwatch.clients import Git
from coinwatch.settings import logger
from coinwatch.src.szz.git_parser import GitParser


class SZZ:
    """SZZ is an algorithm used for finding bug introducing commits in VCS."""

    def __init__(self, repo: Git, commits: List[str]):
        self.repo = repo
        self.commits = commits
        # TODO prepare multiprocessing

    def run(self) -> List[Tuple[str, str]]:
        logger.info("Running SZZ algorithm.")

        annotated_files = {}
        for commit in self.commits:
            prev_commit = self.get_first_from_generator(self.repo.rev_list(commit_id=commit + "~1"))[0]
            commit_diff = self.repo.diff(prev_commit, commit)
            commit_diff = GitParser.parse_diff(commit_diff)
            annotated_files.update({commit: self.annotate_files(commit, commit_diff)})
        logger.info("SZZ annotation done.")

        fix_bug_commit_pairs = self.get_pairs(annotated_files)
        logger.info("SZZ done.")

        return fix_bug_commit_pairs

    @staticmethod
    def get_first_from_generator(gen: Generator):
        val = next(gen)
        del gen
        return val

    def annotate_files(self, commit: str, commit_diff: dict) -> dict:
        """Get fix-bug pairs for each file changed by commit.

        {
            file_1: [
                [prev_commit_hash, ...],
                ...
            ],
            file_2: [...],
            ...
        }

        Args:
            commit (str): fixing commit
            commit_diff (dict): diff of fixing commit

        Returns:
            Dictionary, list of versions affecting each line in each file affected.
        """
        annotated_files = {}
        for filename in commit_diff["affected_files"]:
            file_diff = commit_diff[filename]
            annotated_files[filename] = self.annotate_lines(commit, filename, file_diff)

        return annotated_files

    def annotate_lines(self, commit: str, filename: str, file_diff: dict) -> List[List[str]]:
        prev_commit_blame = self.get_first_from_generator(self.repo.rev_list(commit_id=commit + "~1", file=filename))[0]
        prev_commit_blame = self.repo.annotate(prev_commit_blame, filename)
        prev_commit_blame = GitParser.parse_annotation(prev_commit_blame)

        annotated_lines = []
        for diff in file_diff["affected_lines"]:
            """There are 3 possible scenarios:
            1. Addition
            2. Deletion
            3. Equal Modification
            4. Unequal Modification
            """
            a_line, a_len = diff["a"]
            b_line, b_len = diff["b"]
            if a_len == 0:  # addition
                annotated_lines += [[num, "A"] for num in range(b_line, b_line + b_len)]
            elif b_len == 0:  # deletion
                annotated_lines += [[num, "D", prev_commit_blame[num - 1][0]] for num in range(a_line, a_line + a_len)]
            elif a_len == b_len:  # equal modification
                a_len = a_len or 1
                b_len = b_len or 1
                annotated_lines += [
                    [a_num, "E", prev_commit_blame[b_num - 1][0]]
                    for a_num, b_num in zip(range(a_line, a_line + a_len), range(b_line, b_line + b_len))
                ]
            else:  # unequal modification
                annotated_lines += [
                    [b_num, "U", prev_commit_blame[b_num - 1][0]] for b_num in range(b_line, b_line + b_len)
                ]

        return annotated_lines

    def get_pairs(self, candidates: Dict[str, Dict]) -> List[Tuple[str, str]]:
        # TODO
        ...
