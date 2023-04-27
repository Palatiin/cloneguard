# File: api/bug.py
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: Bug table API

from fastapi import APIRouter, Path

import coinwatch.src.db.crud as crud
from coinwatch.api.models import (
    BugModel,
    BugResponse,
    MultiBugResponse,
    NotFoundError,
    NotFoundErrorResponse,
    ResourceUnavailableErrorResponse,
    ValidationError,
    ValidationErrorResponse,
)
from coinwatch.api.schemas import UpdateBugSchema
from coinwatch.src.async_interface import update_bug
from coinwatch.src.db.session import db_session

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


@router.get(
    path="/{id}",
    responses={
        200: {
            "model": BugResponse,
            "description": BugResponse.__doc__,
        },
        404: {
            "model": NotFoundErrorResponse,
            "description": NotFoundErrorResponse.__doc__,
        },
        503: {
            "model": ResourceUnavailableErrorResponse,
            "description": ResourceUnavailableErrorResponse.__doc__,
        },
    },
)
async def get_bug(id: str = Path(..., title="Bug ID", description="ID of the bug to fetch")):
    try:
        bug = crud.bug.get_cve(db_session, id)
        if not bug:
            return NotFoundErrorResponse().response(message=f"Bug with ID {id} not found.")
        return BugResponse(
            bug=BugModel(
                index=0,
                id=bug.cve_id,
                fix_commit=bug.fix_commit,
                patch=bug.patch or "",
                code=bug.code or "",
                verified=bug.verified,
            )
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
