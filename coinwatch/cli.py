# cli.py

from typing import List, Tuple

import click
import structlog

import coinwatch.src.db.crud as crud
from coinwatch.clients.cve import CVEClient
from coinwatch.clients.detection_methods import BlockScope, Simian
from coinwatch.clients.git import Git
from coinwatch.src.comparator import Comparator
from coinwatch.src.context_extractor import Context, Extractor
from coinwatch.src.cve_reader import load_references
from coinwatch.src.db.session import DBSession, db_session
from coinwatch.src.fixing_commits import FixCommitFinder
from coinwatch.src.patch_fetcher import PatchCode
from coinwatch.src.schemas import CVE
from coinwatch.src.searcher import Searcher
from coinwatch.src.szz.szz import SZZ
from coinwatch.src.update_repos import get_repo_objects, update_repos

logger = structlog.get_logger(__name__)


def session_wrapper(func):
    def inner_wrapper(*args, **kwargs):
        with DBSession():
            func(*args, **kwargs)

    return inner_wrapper


@click.group()
def cli():
    ...


@cli.command()
@click.argument("cve", required=True, type=str, nargs=1)
@click.argument("repo", required=False, type=str, nargs=1)
@click.argument("simian", required=False, type=bool, nargs=1)
@click.argument("repo_date", required=False, type=str, nargs=1)
def run(cve: str, repo: str = "bitcoin", simian: bool = False, repo_date: str = ""):
    """Run the detection.

    CVE: ID of vulnerability to scan
    REPO: source repository where vulnerability was discovered
    SIMIAN: switch to use tool Simian for clone detection
    REPO_DATE: freeze scanned repositories at this date
    """

    @session_wrapper
    def wrapped_run(cve: str, repo: str, simian: bool, repo_date: str):
        logger.info("cli: Run started.")

        repo: Git = Git(repo)
        fix_commits: List[str] = FixCommitFinder(repo, cve=cve).get_fix_commit()
        logger.info(f"Detected fix commits: {fix_commits}")
        # patch_code: str = input("Input patch code/clone detection test:\n")
        patch_code = 'if (block.vtx.empty() || !block.vtx[0]->IsCoinBase())\n         return state.DoS(100, false, REJECT_INVALID, "bad-cb-missing", false, "first tx is not coinbase");\n     for (unsigned int i = 1; i < block.vtx.size(); i++)\n         if (block.vtx[i]->IsCoinBase())\n             return state.DoS(100, false, REJECT_INVALID, "bad-cb-multiple", false, "more than one coinbase");\n \n     // Check transactions\n     for (const auto& tx : block.vtx)\n-        if (!CheckTransaction(*tx, state, false))\n+        if (!CheckTransaction(*tx, state, true))\n             return state.Invalid(false, state.GetRejectCode(), state.GetRejectReason(),\n                                  strprintf("Transaction check failed (tx hash %s) %s", tx->GetHash().ToString(), state.GetDebugMessage()));\n \n     unsigned int nSigOps = 0;\n     for (const auto& tx : block.vtx)\n     {\n         nSigOps += GetLegacySigOpCount(*tx);\n     }\n     if (nSigOps * WITNESS_SCALE_FACTOR > MAX_BLOCK_SIGOPS_COST)\n         return state.DoS(100, false, REJECT_INVALID, "bad-blk-sigops", false, "out-of-bounds SigOpCount");'
        patch_code = 'qDebug() << __func__ << ": Shutdown finished";\n         Q_EMIT shutdownResult();\n     } catch (const std::exception& e) {\n         handleRunawayException(&e);\n     } catch (...) {\n         handleRunawayException(nullptr);\n     }\n }\n \n-BitcoinApplication::BitcoinApplication(interfaces::Node& node, int &argc, char **argv):\n-    QApplication(argc, argv),\n+static int qt_argc = 1;\n+static const char* qt_argv = "bitcoin-qt";\n+\n+BitcoinApplication::BitcoinApplication(interfaces::Node& node):\n+    QApplication(qt_argc, const_cast<char **>(&qt_argv)),\n     coreThread(nullptr),\n     m_node(node),\n     optionsModel(nullptr),\n     clientModel(nullptr),\n     window(nullptr),\n     pollShutdownTimer(nullptr)'

        cloned_repos: List[Git] = get_repo_objects(source=repo)
        update_repos(cloned_repos, repo_date)

        detection_method = (Simian if simian else BlockScope)(patch_code)
        for clone in cloned_repos:
            detection_result = detection_method.run(clone)
            detection_result = [result for result in detection_result if result[0] is not None]
            logger.info(f"{detection_result=}", repo=clone.repo)

        logger.info("cli: Run finished.")

    return wrapped_run(cve, repo, simian, repo_date)


@cli.command()
@click.argument("cve", required=True, type=str)
@click.argument("repo", required=False, type=str)
def legacy_run(cve: str, repo: str):
    @session_wrapper
    def wrapped_run(cve: str, repo: str):  # noqa
        # cve: CVE = CVEClient().cve_id(cve)

        rs = Simian().run(
            "static GlobalMutex g_warnings_mutex;\nstatic bilingual_str g_misc_warnings GUARDED_BY(g_warnings_mutex);\nstatic bool fLargeWorkInvalidChainFound GUARDED_BY(g_warnings_mutex) = false;",
            "cpp",
            "coinwatch/_cache/clones/bitcoin/**/*.cpp",
        )
        print(rs)

        repository: Git = Git(repo or "git@github.com:bitcoin/bitcoin.git")

        rb = BlockScope(
            """
            #include <warnings.h>

            #include <sync.h>
            #include <util/string.h>
            #include <util/system.h>
            #include <util/translation.h>

            #include <vector>

            + static GlobalMutex g_warnings_mutex;
            + static bilingual_str g_misc_warnings GUARDED_BY(g_warnings_mutex);
            + static bool fLargeWorkInvalidChainFound GUARDED_BY(g_warnings_mutex) = false;

            void SetMiscWarning(const bilingual_str& warning)
            {
                LOCK(g_warnings_mutex);
                g_misc_warnings = warning;
            }

            void SetfLargeWorkInvalidChainFound(bool flag)
            {
                LOCK(g_warnings_mutex);
                fLargeWorkInvalidChainFound = flag;
            }
        """
        ).run(repository)
        print(rb)

        finder = FixCommitFinder(repository, cve, cache=False)
        fix_commits = finder.get_fix_commit()
        logger.info(f"{fix_commits=}")

        szz = SZZ(repository, fix_commits)
        # fix_big_commit_pairs = szz.run()
        pass

    return wrapped_run(cve, repo)


@cli.command()
def db_init():
    from coinwatch.src.db.session import DBSchemaSetup, db_session
    from coinwatch.utils.db_init import init

    with DBSchemaSetup():
        init(db_session)


@cli.command()
def test_searcher():
    from tests.test_context_extraction import test_patch2

    repository: Git = Git("git@github.com:bitcoin/bitcoin.git")

    extractor = Extractor(5)
    patch_context: Tuple[Context, Context] = extractor.extract(test_patch2)

    searcher = Searcher(patch_context, repository)
    sr = searcher.search()

    patch_code = PatchCode(test_patch2.split("\n")).fetch()
    candidate_statuses = [Comparator.determine_patch_application(patch_code, candidate) for candidate in sr]
    pass


@cli.command()
def test():
    def test_run(cve):
        cve: CVE = CVEClient().cve_id(cve)

        repository: Git = Git("git@github.com:bitcoin/bitcoin.git")
        load_references(repository, cve.references)

        finder = FixCommitFinder(cve, repository)
        return finder.get_fix_commit()

    from tests.test import test_cve_fix_commit_pairs

    logger.info("Test CVE scraper + Commit finder")

    for i, test_case in enumerate(test_cve_fix_commit_pairs):
        logger.info(f"================ Test {i:2} ================")

        try:
            test_result = test_run(test_case[0])
            test_eval = test_result == test_case[1]
        except Exception as e:
            test_result = str(e)
            test_eval = False

        if test_eval:
            logger.info("Passed.")
        else:
            logger.error(f"Failed. {test_result}")

    logger.info("Test Context Extractor")
    from tests.test_context_extraction import test_list_context_extraction

    for i, test_case in enumerate(test_list_context_extraction):
        logger.info(f"================ Test {i:2} ================")

        try:
            ext = Extractor(5)
            test_result = ext.extract(test_case[0])
            upper_ctx = [pair[1] for pair in test_result[0].sentence_keyword_pairs]
            lower_ctx = [pair[1] for pair in test_result[1].sentence_keyword_pairs]
            test_eval = upper_ctx == test_case[1][0]
            test_eval &= lower_ctx == test_case[1][1]
        except Exception as e:
            test_result = str(e)
            test_eval = False

        if test_eval:
            logger.info("Passed.")
        else:
            logger.error(f"Failed. {test_result}")


if __name__ == "__main__":
    cli()
