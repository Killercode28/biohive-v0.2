"""
Response Wrapper Service
Implements Section 2.2 of Integration Contract
All API responses MUST follow this structure
"""

from typing import Any, Dict, Optional
from datetime import datetime
from fastapi import status
from fastapi.responses import JSONResponse


def success_response(
    data: Any,
    message: str = "Operation successful",
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """
    Create success response following Section 2.2 format
    
    Args:
        data: Actual response data
        message: Success message
        status_code: HTTP status code (default 200)
    
    Returns:
        JSONResponse with structure:
        {
            "success": true,
            "data": { /* actual response data */ },
            "message": "Operation successful",
            "timestamp": "2026-01-16T14:30:00Z"
        }
    """
    response_body = {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    
    return JSONResponse(
        content=response_body,
        status_code=status_code
    )


def error_response(
    code: str,
    message: str,
    details: Optional[Dict] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """
    Create error response following Section 2.2 format
    
    Args:
        code: Error code (e.g., "VALIDATION_ERROR")
        message: Human-readable error message
        details: Optional additional details
        status_code: HTTP status code (default 400)
    
    Returns:
        JSONResponse with structure:
        {
            "success": false,
            "error": {
                "code": "ERROR_CODE",
                "message": "Human readable message",
                "details": { /* optional context */ }
            },
            "timestamp": "2026-01-16T14:30:00Z"
        }
    """
    error_body = {
        "code": code,
        "message": message
    }
    
    if details:
        error_body["details"] = details
    
    response_body = {
        "success": False,
        "error": error_body,
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    
    return JSONResponse(
        content=response_body,
        status_code=status_code
    )


def validation_error_response(
    field: str,
    message: str,
    value: Any = None
) -> JSONResponse:
    """
    Create validation error response (400 Bad Request)
    Special case of error_response for validation failures
    
    Args:
        field: Field that failed validation
        message: Validation error message
        value: Invalid value (optional)
    
    Returns:
        JSONResponse with 400 status code
    """
    details = {"field": field}
    if value is not None:
        details["value"] = value
    
    return error_response(
        code="VALIDATION_ERROR",
        message=message,
        details=details,
        status_code=status.HTTP_400_BAD_REQUEST
    )


def not_found_response(
    resource: str,
    identifier: str
) -> JSONResponse:
    """
    Create not found error response (404 Not Found)
    
    Args:
        resource: Type of resource (e.g., "node", "report")
        identifier: Resource identifier
    
    Returns:
        JSONResponse with 404 status code
    """
    return error_response(
        code="NOT_FOUND",
        message=f"{resource.capitalize()} not found",
        details={"resource": resource, "identifier": identifier},
        status_code=status.HTTP_404_NOT_FOUND
    )


def unauthorized_response(
    message: str = "Invalid or missing authentication token"
) -> JSONResponse:
    """
    Create unauthorized error response (401 Unauthorized)
    
    Args:
        message: Error message
    
    Returns:
        JSONResponse with 401 status code
    """
    return error_response(
        code="UNAUTHORIZED",
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED
    )


def forbidden_response(
    message: str = "Insufficient permissions"
) -> JSONResponse:
    """
    Create forbidden error response (403 Forbidden)
    
    Args:
        message: Error message
    
    Returns:
        JSONResponse with 403 status code
    """
    return error_response(
        code="FORBIDDEN",
        message=message,
        status_code=status.HTTP_403_FORBIDDEN
    )


def internal_error_response(
    message: str = "An unexpected error occurred",
    details: Optional[Dict] = None
) -> JSONResponse:
    """
    Create internal server error response (500)
    
    Args:
        message: Error message
        details: Optional error details (don't expose sensitive info!)
    
    Returns:
        JSONResponse with 500 status code
    """
    return error_response(
        code="INTERNAL_SERVER_ERROR",
        message=message,
        details=details,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


# HTTP Status Code Constants from Section 2.4
class StatusCodes:
    """
    Standard HTTP status codes from Integration Contract Section 2.4
    """
    OK = 200                      # Successful GET/POST
    CREATED = 201                 # Resource created (not used in our API)
    BAD_REQUEST = 400             # Validation error, malformed JSON
    UNAUTHORIZED = 401            # Invalid/missing token
    FORBIDDEN = 403               # Valid token but insufficient permissions
    NOT_FOUND = 404               # Resource doesn't exist
    INTERNAL_SERVER_ERROR = 500   # Unexpected backend error