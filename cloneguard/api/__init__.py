# File: api/__init__.py
# Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: API module

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cloneguard.api import bug, detection, health, project

# initialize app
app = FastAPI(
    title="CloneGuard API",
    docs_url="/api/v1/docs/openapi",
    redoc_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routes
app.include_router(health.router)
app.include_router(bug.router)
app.include_router(detection.router)
app.include_router(project.router)
