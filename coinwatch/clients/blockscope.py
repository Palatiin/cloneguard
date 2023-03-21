# blockscope.py

from coinwatch.clients.git import Git
from coinwatch.src.common import log_wrapper
from coinwatch.src.comparator import Comparator
from coinwatch.src.context_extractor import Extractor
from coinwatch.src.patch_fetcher import PatchCode
from coinwatch.src.searcher import Searcher


class BlockScope:
    def __init__(self, patch: str):
        self.patch_context = Extractor(5).extract(patch=patch)
        self.patch_code = PatchCode(patch.splitlines()).fetch()

    @log_wrapper
    def run(self, repo: Git):
        search_result = Searcher(self.patch_context, repo).search()
        return [Comparator.determine_patch_application(self.patch_code, candidate) for candidate in search_result]
