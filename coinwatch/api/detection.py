# File: api/detection.py
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: Detection method execution API

from fastapi import APIRouter, Path

import coinwatch.src.db.crud as crud
from coinwatch.api.models import (
    DetectionExecutedResponse,
    DetectionStatusResponse,
    InternalServerError,
    InternalServerErrorResponse,
    ResourceUnavailableErrorResponse,
    SearchResponse,
    SearchResultModel,
    ValidationError,
    ValidationErrorResponse,
)
from coinwatch.api.schemas import DetectionMethodExecutionSchema, SearchRequestSchema
from coinwatch.src.async_interface import execute_detection_method, get_status, search_bugs
from coinwatch.src.db.session import db_session

router = APIRouter(
    prefix="/api/v1/detection",
    tags=[__name__.split(".")[-1].capitalize()],
)


@router.post(
    path="/search",
    responses={
        201: {"model": SearchResponse, "description": SearchResponse.__doc__},
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
        500: {
            "model": InternalServerErrorResponse,
            "description": InternalServerErrorResponse.__doc__,
        },
        503: {
            "model": ResourceUnavailableErrorResponse,
            "description": ResourceUnavailableErrorResponse.__doc__,
        },
    },
)
async def execute(data: DetectionMethodExecutionSchema):
    try:
        await execute_detection_method(data)
        return DetectionExecutedResponse()
    except ValidationError as e:
        return ValidationErrorResponse().response(message=str(e))
    except InternalServerError as e:
        return InternalServerErrorResponse().response(message=str(e))
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
)
async def status():
    try:
        _status = await get_status()
        return DetectionStatusResponse(status=_status)
    except InternalServerError as e:
        return InternalServerErrorResponse().response(message=str(e))
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))
