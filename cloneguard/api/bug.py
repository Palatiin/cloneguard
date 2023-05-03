# File: api/bug.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: Bug table API

from fastapi import APIRouter, Path

import cloneguard.src.db.crud as crud
from cloneguard.api.models import (
    BugModel,
    BugResponse,
    MultiBugResponse,
    NotFoundError,
    NotFoundErrorResponse,
    ResourceUnavailableErrorResponse,
    ValidationError,
    ValidationErrorResponse,
)
from cloneguard.api.schemas import UpdateBugSchema
from cloneguard.src.async_interface import update_bug
from cloneguard.src.db.session import db_session

router = APIRouter(
    prefix="/api/v1/bug",
    tags=[__name__.split(".")[-1].capitalize()],
)


@router.get(
    path="/fetch_all",
    responses={
        200: {
            "model": MultiBugResponse,
            "description": MultiBugResponse.__doc__,
        },
        503: {
            "model": ResourceUnavailableErrorResponse,
            "description": ResourceUnavailableErrorResponse.__doc__,
        },
    },
    description="Fetch all bugs stored in the database.",
)
async def get_bugs():
    try:
        bugs = crud.bug.get_all(db_session)
        return MultiBugResponse(
            bugs=[
                BugModel(
                    index=i + 1,
                    id=bug.cve_id,
                    fix_commit=bug.fix_commit,
                    patch=bug.patch or "",
                    code=bug.code or "",
                    verified=bug.verified,
                )
                for i, bug in enumerate(bugs)
            ]
        )
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))


@router.post(
    path="/update",
    status_code=200,
    responses={
        200: {
            "model": BugResponse,
            "description": BugResponse.__doc__,
        },
        404: {
            "model": NotFoundErrorResponse,
            "description": NotFoundErrorResponse.__doc__,
        },
        422: {
            "model": ValidationErrorResponse,
            "description": ValidationErrorResponse.__doc__,
        },
        503: {
            "model": ResourceUnavailableErrorResponse,
            "description": ResourceUnavailableErrorResponse.__doc__,
        },
    },
    description="Update fix commit, patch or code of the bug in the database.",
)
async def update(data: UpdateBugSchema):
    try:
        bug: BugModel = await update_bug(data)
        return BugResponse(bug=bug)
    except NotFoundError as e:
        return NotFoundErrorResponse().response(message=str(e))
    except ValidationError as e:
        return ValidationErrorResponse().response(message=str(e))
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))
