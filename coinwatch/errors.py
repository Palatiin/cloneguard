# File: errors.py
# Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
# Date: 2023-04-26
# Description: Error classes


class CGApiError(Exception):
    code = None
    detail = {}


class NotFoundError(CGApiError):
    code = "not_found"


class ValidationError(CGApiError):
    code = "validation_error"


class MissingValue(ValidationError):
    code = "missing_value"


class InternalServerError(CGApiError):
    code = "internal_server_error"


class ResourceUnavailableError(CGApiError):
    code = "resource_unavailable"
