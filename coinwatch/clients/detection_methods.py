# simian.py

import base64
import os
import re
import subprocess
from dataclasses import dataclass
from typing import List

import structlog

import coinwatch.src.db.crud as crud
from coinwatch.clients.git import Git
from coinwatch.settings import CONTEXT_LINES
from coinwatch.src.common import log_wrapper
from coinwatch.src.comparator import Comparator
from coinwatch.src.context_extractor import Extractor
from coinwatch.src.db.schema import Bug, Detection
from coinwatch.src.db.session import db_session
from coinwatch.src.patch_fetcher import PatchCode
from coinwatch.src.searcher import Searcher

logger = structlog.get_logger()


@dataclass
class SimianDetection:
    start: str
    end: str
    file: str


class Simian:
    simian_jar_path = "coinwatch/simian-2.5.10.jar"
    _re_duplicate_block = re.compile(r"Found.*?(?=Found)", flags=re.S)
    _re_duplicate_lines = re.compile(r"\s*Between\s*lines\s*(\d+)\s*and\s*(\d*)\s*in\s*(.*?)\n")

    def __init__(self, source: Git, bug: Bug):
        if not os.path.exists(f"{self.simian_jar_path}"):
            logger.error("clients: simian: Simian not found.")
            return
        self.threshold = bug.code.count("\n") or 1  # threshold must be > 0
        self.test_file = f"tmp.simian"
        with open(self.test_file, "w", encoding="UTF-8") as file:
            file.write(base64.b64decode(bug.code).decode("utf-8"))

        logger.info("clients: detection_methods: Simian ready.")

    @log_wrapper
    def run(self, repo: Git) -> List[SimianDetection]:
        files = f"{repo.path_to_repo}/**/*.{repo.language}"
        command = ["java", "-jar", self.simian_jar_path, f"-threshold={self.threshold}", self.test_file, files]
        logger.info(f"clients: detection_methods: simian exec: {' '.join(command)}")
        process = subprocess.run(command, stdout=subprocess.PIPE)
        result = process.stdout.decode(errors="replace")

        detections = []
        for block in self._re_duplicate_block.finditer(result):
            _detections = []
            for detection in self._re_duplicate_lines.finditer(block.group(0)):
                _detections.append(SimianDetection(*detection.groups()))
            if f"{os.getcwd()}/{self.test_file}" not in [d.file for d in _detections]:
                continue
            detections += _detections
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
        self.patch_contexts = [extractor.extract(patch=patch) for patch in patches]
        self.patch_codes = [PatchCode(patch).fetch() for patch in patches]
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

        i: int = 0
        for context, code in zip(self.patch_contexts, self.patch_codes):
            i += 1
            search_result = Searcher(context, repo).search(len(code.code))
            applications = [Comparator.determine_patch_application(code, candidate) for candidate in search_result]
            applications = [application for application in applications if application[0] is not None]
            logger.info(f"Patch part application statuses: {applications}", repo=repo.repo)
            if not applications:
                patch_applications.append(())
                continue
            # select the one with the highest similarity, thus the highest confidence
            patch_applications.append(max(applications, key=lambda x: x[1]))

        logger.info(f"Applied patch: {patch_applications}", repo=repo.repo)

        vulnerable = [] if not patch_applications[0] else [res for res in patch_applications if not res[0]]
        not_applied = None if not vulnerable else max(vulnerable, key=lambda x: x[1])
        if not_applied:
            crud.detection.create(db_session, Detection(confidence=not_applied[1], bug=self.bug.id, project=repo.id))
        return patch_applications
