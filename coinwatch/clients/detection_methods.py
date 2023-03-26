# simian.py

import os
import re
import subprocess
from dataclasses import dataclass
from typing import List

import structlog

from coinwatch.clients.git import Git
from coinwatch.src.common import log_wrapper
from coinwatch.src.comparator import Comparator
from coinwatch.src.context_extractor import Extractor
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

    def __init__(self, code: str):
        if not os.path.exists(f"{self.simian_jar_path}"):
            logger.error("clients: simian: Simian not found.")
            return
        self.threshold = code.count("\n") or 1  # threshold must be > 0
        self.test_file = f"tmp.simian"
        with open(self.test_file, "w", encoding="UTF-8") as file:
            file.write(code)

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
    def __init__(self, patch: str):
        self.patch_context = Extractor(5).extract(patch=patch)
        self.patch_code = PatchCode(patch.splitlines()).fetch()
        logger.info("clients: detection_methods: BlockScope ready.")

    @log_wrapper
    def run(self, repo: Git):
        search_result = Searcher(self.patch_context, repo).search()
        return [Comparator.determine_patch_application(self.patch_code, candidate) for candidate in search_result]
