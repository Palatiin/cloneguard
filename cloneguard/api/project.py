# File: api/project.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: Projects table API

from fastapi import APIRouter

import cloneguard.src.db.crud as crud
from cloneguard.api.models import (
    MultiProjectResponse,
    ProjectModel,
    ProjectResponse,
    ResourceUnavailableErrorResponse,
    ValidationError,
    ValidationErrorResponse,
)
from cloneguard.api.schemas import NewProjectSchema
from cloneguard.src.async_interface import register_project
from cloneguard.src.db.session import db_session

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
    description="Fetch all projects stored in the database.",
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
    description="Register a new project.",
)
async def register(data: NewProjectSchema):
    try:
        project: ProjectModel = await register_project(data)
        return ProjectResponse(project=project)
    except ValidationError as e:
        return ValidationErrorResponse().response(message=str(e))
    except Exception as e:
        return ResourceUnavailableErrorResponse().response(message=str(e))
