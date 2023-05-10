# File: clients/detection_method.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-03-26
# Description: Implementation of detection method components.

import base64
import os
import re
import subprocess
from dataclasses import dataclass
from typing import List

import structlog

import cloneguard.src.db.crud as crud
from cloneguard.clients.git import Git
from cloneguard.settings import CONTEXT_LINES
from cloneguard.src.common import log_wrapper
from cloneguard.src.comparator import Comparator
from cloneguard.src.context_extractor import Extractor
from cloneguard.src.db.schema import Bug, Detection
from cloneguard.src.db.session import db_session
from cloneguard.src.patch_fetcher import PatchCode
from cloneguard.src.searcher import Searcher

logger = structlog.get_logger()


@dataclass
class SimianDetection:
    start: str
    end: str
    file: str


class Simian:
    simian_jar_path = "cloneguard/simian-2.5.10.jar"
    _re_duplicate_block = re.compile(r"Found.*?(?=Found)", flags=re.S)
    _re_duplicate_lines = re.compile(r"\s*Between\s*lines\s*(\d+)\s*and\s*(\d+)\s*in\s*(\S+)")

    _known_languages = ["java", "c", "cpp"]

    def __init__(self, source: Git, bug: Bug):
        if not os.path.exists(f"{self.simian_jar_path}"):
            logger.error("clients: simian: Simian not found.")
            return
        code = base64.b64decode(bug.code).decode("ascii")
        self.threshold = code.count("\n") or 1  # threshold must be > 0
        self.test_file = f"tmp.simian.{source.language}"
        with open(self.test_file, "w", encoding="UTF-8") as file:
            file.write(code)

        logger.info("clients: detection_methods: Simian ready.")

    @log_wrapper
    def run(self, repo: Git) -> List[SimianDetection]:
        """Run Simian detection method.

        Args:
            repo (Git): Cloned repository, which will be analysed

        Returns:
            Detection results.
        """
        files = f"{repo.path_to_repo}/**/*.{repo.language}"
        command = [
            "java",
            "-jar",
            self.simian_jar_path,
            f"-threshold={self.threshold}",
        ]
        command += [f"-language={repo.language}"] if repo.language in self._known_languages else []
        command += [self.test_file, files]
        logger.info(f"clients: detection_methods: simian exec: {' '.join(command)}")
        process = subprocess.run(command, stdout=subprocess.PIPE)
        result = process.stdout.decode(errors="replace")

        detections = []
        cwd = os.getcwd()

        # parse output
        for block in self._re_duplicate_block.finditer(result):
            _detections = []
            is_test_duplicate = False

            for detection in self._re_duplicate_lines.finditer(block.group(0)):
                _det = SimianDetection(*detection.groups())
                _detections.append(_det)

                if _det.file == f"{cwd}/{self.test_file}":
                    is_test_duplicate = True

            if not is_test_duplicate:
                continue
            detections += _detections

        if detections:
            logger.info(f"Applied patch: [{(False, 1.0, '')}]", repo=repo.repo)
        else:
            logger.info(f"Applied patch: [{(True, 1.0, '')}]", repo=repo.repo)
        return detections


class BlockScope:
    def __init__(self, source: Git, bug: Bug):
        """Initialize detection method BlockScope.

        Args:
            source (Git): Repository, where the bug was discovered
            bug (Bug): The discovered bug
        """
        self.bug = bug
        extractor = Extractor(source.language, CONTEXT_LINES)
        patches = (
            [base64.b64decode(bug.patch).decode("utf-8")]
            if bug.patch
            else extractor.get_patch_from_commit(source, bug.commits[0])
        )
        if bug.patch and bug.patch.startswith("commit "):
            patches = extractor.get_patch_from_commit_str(bug.patch)
        self.patch_contexts = []
        self.patch_codes = []
        for patch in patches:
            try:
                context = extractor.extract(patch=patch)
                code = PatchCode(patch).fetch()
                self.patch_contexts.append(context)
                self.patch_codes.append(code)
            except Exception as e:
                logger.warning(f"clients: detection_methods: BlockScope: {e}")
                continue
        logger.info("clients: detection_methods: BlockScope ready.")

    @log_wrapper
    def run(self, repo: Git) -> list:
        """Run the detection method.

        Args:
            repo (Git): Cloned repository, which will be analysed

        Returns:
            Detection results.
        """
        patch_applications: list = []
        for context, code in zip(self.patch_contexts, self.patch_codes):
            # search for code candidates in target repository
            search_result = Searcher(context, repo).search(len(code.code))

            # evaluate patch applications for each candidate code
            applications = [Comparator.determine_patch_application(code, candidate) for candidate in search_result]
            applications = list(filter(lambda x: x[0] is not None, applications))
            logger.info(f"Patch part application statuses: {applications}", repo=repo.repo)

            if not applications:
                # clone not detected
                patch_applications.append(())
                continue

            # select the one with the highest similarity, thus the highest confidence
            patch_applications.append(max(applications, key=lambda x: x[1]))

        logger.info(f"Applied patch: {patch_applications}", repo=repo.repo)

        # filter out empty results
        patch_applications = list(filter(lambda x: x, patch_applications))

        # check if any patch part is not applied
        vulnerable = [res for res in patch_applications if not res[0]]

        # if any part is not applied, the repository did not apply the patch, thus still potentially vulnerable
        not_applied = None if not vulnerable else max(vulnerable, key=lambda x: x[1])
        if not_applied:
            crud.detection.create(db_session, Detection(confidence=not_applied[1], bug=self.bug.id, project=repo.id))
        return patch_applications
