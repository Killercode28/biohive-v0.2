"""
Response Wrapper Service
Implements Section 2.2 of Integration Contract
All API responses MUST follow this structure
"""

from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import status
from fastapi.responses import JSONResponse


# ------------------------------------------------------------------
# SUCCESS RESPONSE
# ------------------------------------------------------------------

def success_response(
    data: Any,
    message: str = "Operation successful",
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """
    Standard success response
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": data,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


# ------------------------------------------------------------------
# ERROR RESPONSES
# ------------------------------------------------------------------

def error_response(
    code: str,
    message: str,
    details: Optional[Dict] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    """
    Standard error response
    """
    error_body = {
        "code": code,
        "message": message,
    }

    if details is not None:
        error_body["details"] = details

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": error_body,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


def validation_error_response(
    field: str,
    message: str,
    value: Any = None,
) -> JSONResponse:
    details = {"field": field}
    if value is not None:
        details["value"] = value

    return error_response(
        code="VALIDATION_ERROR",
        message=message,
        details=details,
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def not_found_response(resource: str, identifier: str) -> JSONResponse:
    return error_response(
        code="NOT_FOUND",
        message=f"{resource.capitalize()} not found",
        details={"resource": resource, "identifier": identifier},
        status_code=status.HTTP_404_NOT_FOUND,
    )


def unauthorized_response(
    message: str = "Invalid or missing authentication token",
) -> JSONResponse:
    return error_response(
        code="UNAUTHORIZED",
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def forbidden_response(
    message: str = "Insufficient permissions",
) -> JSONResponse:
    return error_response(
        code="FORBIDDEN",
        message=message,
        status_code=status.HTTP_403_FORBIDDEN,
    )


def internal_error_response(
    message: str = "An unexpected error occurred",
    details: Optional[Dict] = None,
) -> JSONResponse:
    return error_response(
        code="INTERNAL_SERVER_ERROR",
        message=message,
        details=details,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ------------------------------------------------------------------
# CONVENIENCE ALIAS (USED BY ROUTES)
# ------------------------------------------------------------------

def success(data: Any) -> JSONResponse:
    """
    Shorthand used by routes:
    return success(data)
    """
    return success_response(data)


# ------------------------------------------------------------------
# STATUS CODES (CONTRACT SECTION 2.4)
# ------------------------------------------------------------------

class StatusCodes:
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500
