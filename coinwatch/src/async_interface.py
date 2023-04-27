# File: src/async_interface.py
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-27
# Description: Async interface for API

import os
from datetime import datetime as dt
from multiprocessing import Process

from structlog import get_logger

import coinwatch.settings as settings
import coinwatch.src.db.crud as crud
from coinwatch.api.models import (
    BugModel,
    DetectionModel,
    DetectionStatusModel,
    InternalServerError,
    NotFoundError,
    ProjectModel,
    SearchResultModel,
    ValidationError,
)
from coinwatch.api.schemas import DetectionMethodExecutionSchema, NewProjectSchema, SearchRequestSchema, UpdateBugSchema
from coinwatch.clients.detection_methods import BlockScope, Simian
from coinwatch.clients.git import Git
from coinwatch.src.db.schema import Project
from coinwatch.src.db.session import db_session
from coinwatch.src.fixing_commits import FixCommitFinder
from coinwatch.src.update_repos import get_repo_objects, update_repos

logger = get_logger(__name__)


async def register_project(data: NewProjectSchema) -> ProjectModel:
    try:
        if not data.url or not data.language:
            raise ValidationError("Missing value: url")

        project_info = Git._re_url_contents.search(data.url).groups()  # noqa

        if crud.project.get_by_name(db_session, project_info[1]):
            raise ValidationError("Project already exists")

        if data.parent and not (parent := crud.project.get_by_name(db_session, data.parent)):
            raise ValidationError("Parent project does not exist")

        project = crud.project.create(
            db_session,
            Project(
                url=data.url,
                name=project_info[1],
                author=project_info[0],
                language=data.language,
                parent_id=None if not data.parent else parent.id,
            ),
        )

        def clone_project(p: Project):
            Git(p)

        clone_process = Process(target=clone_project, args=project)
        clone_process.start()

        return ProjectModel(
            index=0,
            name=project.name,
            owner=project.author,
            language=project.language,
            parent=data.parent or "",
        )

    except ValidationError as e:
        raise e
    except Exception as e:
        raise e


async def update_bug(data: UpdateBugSchema) -> BugModel:
    try:
        if not data.id:
            raise ValidationError("Missing value: id")
        if not data.patch and not data.fix_commit:
            raise ValidationError("Missing value: patch or fix_commit")

        bug = crud.bug.get(db_session, data.id)
        if not bug:
            raise NotFoundError()

        if data.method == "simian":
            if data.patch:
                bug.code = data.patch
        elif data.patch:
            bug.patch = data.patch

        if data.fix_commit:
            bug.commits = data.fix_commit

        crud.bug.update(db_session, bug)

        return BugModel(
            index=0,
            id=bug.cve_id,
            fix_commit=bug.fix_commit,
            patch=bug.patch or "",
            code=bug.code or "",
            verified=bug.verified,
        )

    except NotFoundError as e:
        raise e
    except ValidationError as e:
        raise e
    except Exception as e:
        raise e


async def search_bugs(data: SearchRequestSchema) -> SearchResultModel:
    try:
        if not data.bug_id or not data.project_name:
            raise ValidationError("Missing value: bug_id or project_name")

        project = crud.project.get_by_name(db_session, data.project_name)
        if not project:
            raise ValidationError("Project does not exist")

        try:
            project = Git(project)

            bug = FixCommitFinder(project, data.bug_id).get_bug()
        except Exception as e:
            raise InternalServerError(e)

        return SearchResultModel(
            commits=bug.commits,
            patch=bug.patch,
        )

    except ValidationError as e:
        raise e
    except InternalServerError as e:
        raise e
    except Exception as e:
        raise e


async def execute_detection_method(data: DetectionMethodExecutionSchema):
    def execute(d: DetectionMethodExecutionSchema):
        logger.info("Starting detection method...")
        bug = crud.bug.get(db_session, d.bug_id)
        bug = bug.copy()
        bug.commits = d.commit
        if d.method == "simian":
            bug.code = d.patch
        else:
            bug.patch = d.patch

        repo = crud.project.get_by_name(db_session, d.project_name)
        repo = Git(repo)

        clones = get_repo_objects(source=repo)
        update_repos(clones, d.date)

        for clone in clones:
            detection_method = (Simian if d.detect_method == "simian" else BlockScope)(repo, bug)
            detection_method.run(clone)

        logger.info("Detection method finished.")

    try:
        if not data.bug_id or not data.commit or not data.patch:
            raise ValidationError("Missing value: bug_id or commit or patch")

        try:
            if not os.path.exists(f"{settings.CACHE_PATH}/logs"):
                os.makedirs(f"{settings.CACHE_PATH}/logs", exist_ok=True)
            settings.timestamp = dt.now().timestamp()
            settings.configure_logging(filename=f"{settings.CACHE_PATH}/logs/{settings.timestamp}.log")

            detection_process = Process(target=execute, args=data)
            detection_process.start()

        except Exception as e:
            raise InternalServerError(e)

    except ValidationError as e:
        raise e
    except InternalServerError as e:
        raise e
    except Exception as e:
        raise e


async def get_status():
    try:
        logs = ""
        if os.path.exists(f"{settings.CACHE_PATH}/logs"):
            log_file = sorted(os.listdir(f"{settings.CACHE_PATH}/logs"), reverse=True)[0]
            with open(f"{settings.CACHE_PATH}/logs/{log_file}", "r") as f:
                logs = f.read()

        detections = crud.detection.get_all_after(db_session, int(log_file.split(".")[0]))

        return DetectionStatusModel(
            logs=logs,
            detections=[
                DetectionModel(
                    project_name=crud.project.get(db_session, detection.project).name,
                    confidence=detection.confidence,
                    location="{}:{}".format(detection.file, detection.line),
                )
                for detection in detections
            ],
        )

    except ValidationError as e:
        raise e
    except InternalServerError as e:
        raise e
    except Exception as e:
        raise e
