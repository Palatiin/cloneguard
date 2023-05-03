# File: api/schemas.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: API payload schemas

from pydantic import Field

from cloneguard.api.models import CGApiModel


class NewProjectSchema(CGApiModel):
    """New project schema."""

    url: str = Field(
        default=...,
        title="Clone URL",
        description="Clone URL of the project.",
        example="https://github.com/bitcoin/bitcoin.git",
    )

    language: str = Field(
        default=...,
        title="Programming language of the project",
        description="Programming language of the project.",
        example="cpp",
    )

    parent: str = Field(
        default=None,
        title="Parent project",
        description="Parent project.",
        example="bitcoin",
    )


class UpdateBugSchema(CGApiModel):
    """Update bug schema."""

    id: str = Field(
        default=...,
        title="Bug ID",
        description="ID of the bug to update.",
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
        title="Patch",
        description="Patch code, base64 encoded.",
        example="",
    )

    method: str = Field(
        default=...,
        title="Detection method",
        description="Detection method using the patch - chooses where the patch will be stored in DB.",
        example="blockscope",
    )


class SearchRequestSchema(CGApiModel):
    """Search request schema."""

    bug_id: str = Field(
        default=...,
        title="Bug ID",
        description="ID of the bug to search for.",
        example="CVE-2018-17144",
    )

    project_name: str = Field(
        default=...,
        title="Source project name",
        description="Source project name where the bug was discovered.",
        example="bitcoin",
    )


class ShowCommitSchema(CGApiModel):
    """Show commit patch schema."""

    project_name: str = Field(
        default=...,
        title="Source project name",
        description="Source project name where the commit should be searched.",
        example="bitcoin",
    )

    commit: str = Field(
        default=...,
        title="Commit hash",
        description="Commit hash to fetch.",
        example="a1b2c3d4e5",
    )


class DetectionMethodExecutionSchema(CGApiModel):
    """Detection method execution request schema."""

    bug_id: str = Field(
        default=...,
        title="Bug ID",
        description="ID of the bug to execute the detection method on and associate results.",
        example="CVE-2018-17144",
    )

    project_name: str = Field(
        default=...,
        title="Project name",
        description="Name of the project where the bug was discovered.",
        example="bitcoin",
    )

    commit: str = Field(
        default="",
        title="Commit hash",
        description="Commit hash to execute the detection method on.",
        example="a1b2c3d4e5",
    )

    patch: str = Field(
        default="",
        title="Patch code",
        description="Code for clone detection method.",
        example="",
    )

    method: str = Field(
        default="blockscope",
        title="Detection method",
        description="Detection method to execute.",
        example="blockscope",
    )

    date: str = Field(
        default="",
        title="Project version date",
        description="Project version date to be initialized.",
        example="2020-01-01",
    )
