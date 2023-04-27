# File: api/project.py
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: Projects table API

from fastapi import APIRouter

import coinwatch.src.db.crud as crud
from coinwatch.api.models import (
    MultiProjectResponse,
    NotFoundErrorResponse,
    ProjectModel,
    ProjectResponse,
    ResourceUnavailableErrorResponse,
    ValidationError,
    ValidationErrorResponse,
)
from coinwatch.api.schemas import NewProjectSchema
from coinwatch.src.async_interface import register_project
from coinwatch.src.db.session import db_session

router = APIRouter(
    prefix="/api/v1/project",
    tags=[__name__.split(".")[-1].capitalize()],
)


@router.get(
    path="/fetch_all",
    responses={
        200: {
            "model": MultiProjectResponse,
            "description": MultiProjectResponse.__doc__,
        },
        503: {
            "model": ResourceUnavailableErrorResponse,
            "description": ResourceUnavailableErrorResponse.__doc__,
        },
    },
)
async def get_projects():
    try:
        projects = crud.project.get_all(db_session)
        return MultiProjectResponse(
            projects=[
                ProjectModel(
                    index=i + 1,
                    name=project.name,
                    owner=project.author,
                    language=project.language,
                    parent="" if not project.parent_id else crud.project.get(db_session, project.parent_id).name,
                )
                for i, project in enumerate(projects)
            ]
        )
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))


@router.get(
    path="/{name}",
    responses={
        200: {
            "model": ProjectResponse,
            "description": ProjectResponse.__doc__,
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
async def get_project(name: str):
    try:
        project = crud.project.get_by_name(db_session, name)
        if not project:
            return NotFoundErrorResponse().response(message=f"Project with name {name} not found.")
        return ProjectResponse(
            project=ProjectModel(
                index=0,
                name=project.name,
                owner=project.author,
                language=project.language,
                parent="" if not project.parent_id else crud.project.get(db_session, project.parent_id).name,
            )
        )
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))


@router.post(
    path="/register",
    status_code=201,
    responses={
        201: {
            "model": ProjectResponse,
            "description": ProjectResponse.__doc__,
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
async def register_project(data: NewProjectSchema):
    try:
        project: ProjectModel = await register_project(data)
        return ProjectResponse(project=project)
    except ValidationError as e:
        return ValidationErrorResponse().response(message=str(e))
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))
