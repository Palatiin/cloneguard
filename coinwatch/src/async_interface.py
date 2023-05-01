# File: src/async_interface.py
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-27
# Description: Async interface for API

import os
import re
import base64
from datetime import datetime as dt
from multiprocessing import Process

import orjson
import redis
from rq import Queue
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
    ShowCommitModel,
)
from coinwatch.api.schemas import (
    DetectionMethodExecutionSchema,
    NewProjectSchema,
    SearchRequestSchema,
    ShowCommitSchema,
    UpdateBugSchema,
)
from coinwatch.clients.git import Git
from coinwatch.src.db.schema import Project
from coinwatch.src.db.session import db_session
from coinwatch.src.fixing_commits import FixCommitFinder
from coinwatch.tasks import clone_task, execute_task
from coinwatch.settings import REDIS_HOST, REDIS_PORT, CONTEXT_LINES

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

        try:
            redis_conn = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
            queue = Queue("task_queue", connection=redis_conn, default_timeout=600)
            queue.enqueue(clone_task, project.name)

        except Exception as e:
            raise InternalServerError(e)

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

        bug = crud.bug.get_cve(db_session, data.id)
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


async def fetch_commit(data: ShowCommitSchema):
    try:
        if not data.commit or not data.project_name:
            raise ValidationError("Missing value: commit or project_name")

        project = crud.project.get_by_name(db_session, data.project_name)
        if not project:
            raise ValidationError("Project is not registered.")

        try:
            project = Git(project)

            commit = project.show(data.commit, quiet=False, context=CONTEXT_LINES * 2)
            if not commit:
                raise NotFoundError("Commit not found.")
        except NotFoundError as e:
            raise e
        except Exception as e:
            raise InternalServerError(e)

        return ShowCommitModel(
            commit=data.commit,
            patch=base64.b64encode(commit.encode("utf-8")),
        )
    except NotFoundError as e:
        raise e
    except ValidationError as e:
        raise e
    except InternalServerError as e:
        raise e
    except Exception as e:
        raise e


async def execute_detection_method(data: DetectionMethodExecutionSchema):
    try:
        if not data.bug_id or not data.commit or not data.patch:
            raise ValidationError("Missing value: bug_id or commit or patch")

        redis_conn = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
        queue = Queue("task_queue", connection=redis_conn, default_timeout=600)
        queue.enqueue(
            execute_task,
            data.bug_id,
            data.commit,
            data.patch,
            data.method,
            data.project_name,
            data.date,
            dt.now().timestamp(),
        )

    except ValidationError as e:
        raise e
    except Exception as e:
        raise e


async def get_status():
    try:
        if os.path.exists(f"{settings.CACHE_PATH}/logs"):
            log_file = sorted(os.listdir(f"{settings.CACHE_PATH}/logs"), reverse=True)[0]
            with open(f"{settings.CACHE_PATH}/logs/{log_file}", "r") as f:
                logs = f.read()
        else:
            raise Exception("No logs found")

        detections = []
        try:
            for match in re.finditer(r"Applied\s*patch:\s*(\[.*?\])\s*repo=(\S+)\b", logs):
                project = match.group(2)
                results = orjson.loads(
                    match.group(1).replace("(", "[").replace(")", "]").replace("False", "false").replace("True", "true")
                )
                detections.extend(
                    [
                        DetectionModel(
                            project_name=project,
                            vulnerable="False" if result[0] else "True",
                            confidence=round(result[1], 3),
                            location="",  # result[2],
                        )
                        for result in results
                        if result
                    ]
                )
        except Exception as e:
            raise InternalServerError(e)

        return DetectionStatusModel(
            logs=logs,
            detection_results=detections,
        )

    except ValidationError as e:
        raise e
    except InternalServerError as e:
        raise e
    except Exception as e:
        raise e
