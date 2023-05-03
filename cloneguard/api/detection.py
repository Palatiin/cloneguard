# File: api/detection.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: Detection method execution API

from fastapi import APIRouter, Path

from cloneguard.api.models import (
    DetectionExecutedResponse,
    DetectionStatusResponse,
    InternalServerError,
    InternalServerErrorResponse,
    ResourceUnavailableErrorResponse,
    SearchResponse,
    SearchResultModel,
    ShowCommitModel,
    ShowCommitResponse,
    ValidationError,
    ValidationErrorResponse,
    NotFoundError,
    NotFoundErrorResponse,
    DetectionStatusModel,
)
from cloneguard.api.schemas import DetectionMethodExecutionSchema, SearchRequestSchema, ShowCommitSchema
from cloneguard.src.async_interface import execute_detection_method, get_status, search_bugs, fetch_commit

router = APIRouter(
    prefix="/api/v1/detection",
    tags=[__name__.split(".")[-1].capitalize()],
)


@router.post(
    path="/search",
    responses={
        200: {"model": SearchResponse, "description": SearchResponse.__doc__},
        422: {
            "model": ValidationErrorResponse,
            "description": ValidationErrorResponse.__doc__,
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": InternalServerErrorResponse.__doc__,
        },
        503: {
            "model": ResourceUnavailableErrorResponse,
            "description": ResourceUnavailableErrorResponse.__doc__,
        },
    },
    description="Find the bug fixing commit in the given repository.",
)
async def search(data: SearchRequestSchema):
    try:
        search_result: SearchResultModel = await search_bugs(data)
        return SearchResponse(search_result=search_result)
    except ValidationError as e:
        return ValidationErrorResponse().response(message=str(e))
    except InternalServerError as e:
        return InternalServerErrorResponse().response(message=str(e))
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))


@router.post(
    path="/show_commit",
    responses={
        200: {
            "model": ShowCommitResponse,
            "description": ShowCommitResponse.__doc__,
        },
        404: {
            "model": NotFoundErrorResponse,
            "description": NotFoundErrorResponse.__doc__,
        },
        422: {
            "model": ValidationErrorResponse,
            "description": ValidationErrorResponse.__doc__,
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": InternalServerErrorResponse.__doc__,
        },
        503: {
            "model": ResourceUnavailableErrorResponse,
            "description": ResourceUnavailableErrorResponse.__doc__,
        },
    },
    description="Show diff of the candidate commit.",
)
async def show_commit(data: ShowCommitSchema):
    try:
        commit: ShowCommitModel = await fetch_commit(data)
        return ShowCommitResponse(commit=commit)
    except NotFoundError as e:
        return NotFoundErrorResponse().response(message=str(e))
    except ValidationError as e:
        return ValidationErrorResponse().response(message=str(e))
    except InternalServerError as e:
        return InternalServerErrorResponse().response(message=str(e))
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))


@router.post(
    path="/execute",
    responses={
        201: {
            "model": None,
            "description": None,
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
    description="Execute detection method on the clones of the given source project.",
)
async def execute(data: DetectionMethodExecutionSchema):
    try:
        await execute_detection_method(data)
        return DetectionExecutedResponse()
    except ValidationError as e:
        return ValidationErrorResponse().response(message=str(e))
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))


@router.get(
    path="/status",
    responses={
        200: {
            "model": DetectionStatusResponse,
            "description": DetectionStatusResponse.__doc__,
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": InternalServerErrorResponse.__doc__,
        },
        503: {
            "model": ResourceUnavailableErrorResponse,
            "description": ResourceUnavailableErrorResponse.__doc__,
        },
    },
    description="Get status of the detection method run.",
)
async def status():
    try:
        _status: DetectionStatusModel = await get_status()
        return DetectionStatusResponse(status=_status)
    except InternalServerError as e:
        return InternalServerErrorResponse().response(message=str(e))
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))
