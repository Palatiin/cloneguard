# File: api/models.py
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: API models

from enum import Enum
from typing import List, Optional, Union

import orjson
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from coinwatch.errors import *
from coinwatch.version import VERSION

BaseModel.__dict__["__init__"].__doc__ = ""


class APIResponse(BaseModel):
    _status_code: int = ...

    version: str = Field(
        default_factory=lambda: VERSION,
        description="API version.",
        example=VERSION,
    )

    def response(self):
        return JSONResponse(status_code=self._status_code, content=orjson.loads(self.json()))


class ErrorDetails(BaseModel):
    code: str = Field(
        default=...,
        title="Error code",
        description="Error identifier (used for tracking).",
    )
    message: str = Field(
        default=...,
        title="Error message",
        description="Human readable generic message.",
    )
    detail: Union[str, list, dict] = Field(
        default={},
        title="Error detail",
        description="Optional additional information.",
        example={},
    )


class CGApiModel(BaseModel):
    class Config:
        underscore_attrs_are_private = True
        validate_assignment = True
        json_loads = orjson.loads
        json_dumps = lambda d, *a, **kw: orjson.dumps(d, *a, **kw).decode()

    def dict_clean(self):
        """Return a "clean" version of the :obj:`dict` representation."""
        return orjson.loads(self.json())


class ErrorCode(str, Enum):
    """Error code enum."""

    NOT_FOUND_ERROR = NotFoundError.code
    VALIDATION_ERROR = ValidationError.code
    INTERNAL_SERVER_ERROR = InternalServerError.code
    RESOURCE_UNAVAILABLE = ResourceUnavailableError.code


# ========================= ERROR models =========================


class ErrorResponse(APIResponse):
    error: ErrorDetails = Field(
        default=...,
        description="Detailed information about the error.",
    )

    def response(self, message: str = None, detail: str = None):
        self.error.detail = detail or self.error.detail
        self.error.message = message or self.error.message
        return super().response()


class NotFoundErrorModel(ErrorDetails):
    code: ErrorCode = ErrorCode.NOT_FOUND_ERROR
    message: str = Field(
        default="Not found.",
        example="Resource not found.",
    )


class ValidationErrorModel(ErrorDetails):
    code: ErrorCode = ErrorCode.VALIDATION_ERROR
    message: str = Field(
        default="Validation error.",
        example="Value '<field>' is not a valid <type>.",
    )


class InternalServerErrorModel(ErrorDetails):
    code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR
    message: str = Field(
        default="Internal server error.",
        example="Internal server error: '<reason>'.",
    )


class ResourceUnavailableErrorModel(ErrorDetails):
    code: ErrorCode = ErrorCode.RESOURCE_UNAVAILABLE
    message: str = Field(
        default="Resource unavailable.",
        example="Resource is currently unavailable.",
    )


# ========================= ERROR responses =========================


class NotFoundErrorResponse(ErrorResponse):
    """Not found error."""

    _status_code: int = 404
    error: NotFoundErrorModel = NotFoundErrorModel()


class ValidationErrorResponse(ErrorResponse):
    """Validation error."""

    _status_code: int = 422
    error: ValidationErrorModel = ValidationErrorModel()


class InternalServerErrorResponse(ErrorResponse):
    """Internal server error."""

    _status_code: int = 500
    error: InternalServerErrorModel = InternalServerErrorModel()


class ResourceUnavailableErrorResponse(ErrorResponse):
    """Resource unavailable error."""

    _status_code: int = 503
    error: ResourceUnavailableErrorModel = ResourceUnavailableErrorModel()


# ========================= OK models =========================


class ProjectModel(CGApiModel):
    """Project table record model."""

    index: int = Field(
        default=...,
        title="Project index",
        description="Project index, relevant for list of projects visualisation.",
        example=1,
    )

    name: str = Field(
        default=...,
        title="Project name",
        description="Project name.",
        example="dogecoin",
    )

    owner: str = Field(
        default=...,
        title="Project owner",
        description="Project owner.",
        example="dogecoin",
    )

    language: str = Field(
        default=...,
        title="Project programming language",
        description="Project programming language.",
        example="cpp",
    )

    parent: str = Field(
        default="",
        title="Parent project ID",
        description="Parent project ID, models hierarchy of clones.",
        example="bitcoin",
    )


class BugModel(CGApiModel):
    """Bug table record model."""

    index: int = Field(
        default=...,
        title="Bug index",
        description="Bug index, relevant for list of bugs visualisation.",
        example=1,
    )

    id: str = Field(
        default=...,
        title="Bug ID",
        description="Bug ID.",
        example="CVE-2018-17144",
    )

    fix_commit: str = Field(
        default="",
        title="Fix commit(s)",
        description="Commits fixing the bug.",
        example="['a1b2c3d4e5']",
    )

    patch: str = Field(
        default="",
        title="Patch code",
        description="Patch code fixing the bug, base64 encoded.",
        example="",
    )

    code: str = Field(
        default="",
        title="Fixed code chunk",
        description="Fixed code chunk, base64 encoded.",
        example="",
    )

    verified: bool = Field(
        default=False,
        title="Verified flag",
        description="Flag indicating whether the bug was verified.",
        example=False,
    )


class SearchResultModel(CGApiModel):
    """Bug fix search results."""

    commits: List[str] = Field(
        default=[],
        title="Fix commit candidates",
        description="List of commit candidates fixing the bug.",
        example=["a1b2c3d4e5"],
    )

    patch: str = Field(
        default="",
        title="Patch code",
        description="Patch code fixing the bug, base64 encoded if available.",
        example="",
    )


class DetectionModel(CGApiModel):
    """Detection table model."""

    project_name: str = Field(
        default=...,
        title="Affected clone",
        description="Affected clone of the source project.",
        example="dogecoin",
    )

    confidence: float = Field(
        default=...,
        title="Result confidence",
        description="Confidence of the detection result.",
        example=0.9,
    )

    location: str = Field(
        default=...,
        title="Location of the clone",
        description="Location where the clone was detected by the detection method - <file>:<start_line>.",
        example="validation.cpp:588",
    )


class DetectionStatusModel(CGApiModel):
    """Detection status model."""

    detection_results: List[DetectionModel] = Field(
        default="[]",
        title="Detection results",
        description="Detection results.",
    )

    logs: str = Field(
        default="",
        title="Log.",
        description="Detection process log.",
    )


# ========================= OK responses =========================


class Pong(APIResponse):
    """Pong."""

    _status_code: int = 200
    pong: bool = True


class ProjectResponse(APIResponse):
    """Single project response."""

    _status_code: int = 200
    project: ProjectModel = ...


class MultiProjectResponse(APIResponse):
    """List of multiple projects response."""

    _status_code: int = 200
    projects: List[ProjectModel] = ...


class BugResponse(APIResponse):
    """Single bug response."""

    _status_code: int = 200
    bug: BugModel = ...


class MultiBugResponse(APIResponse):
    """List of multiple bugs response."""

    _status_code: int = 200
    bugs: List[BugModel] = ...


class SearchResponse(APIResponse):
    """Search response."""

    _status_code: int = 200
    search_result: SearchResultModel = SearchResultModel


class DetectionExecutedResponse(APIResponse):
    """Detection executed response."""

    _status_code: int = 200
    status: str = "Started."


class DetectionStatusResponse(APIResponse):
    """Detection status response."""

    _status_code: int = 200
    status: DetectionStatusModel = ...
