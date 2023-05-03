# File: api/health.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: Health check API

from fastapi import APIRouter

from cloneguard.api.models import Pong

router = APIRouter(
    prefix="/api/v1",
    tags=[__name__.split(".")[-1].capitalize()],
)


@router.get(
    path="/ping",
    responses={200: {"model": Pong, "description": Pong.__doc__}},
    description="Ping the API to see whether it's alive.",
)
async def ping():
    """Ping the API to see whether it's alive."""
    return {"pong": True}
