"""
Custom Application Exceptions and error handlers.
Ensures safe, clear error messages without exposing internal stack traces.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("legal_metrology")


class AppException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, details=details)


class ServiceUnavailableException(AppException):
    def __init__(self, message: str = "Downstream service temporarily unavailable", details: dict = None):
        super().__init__(message=message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)


async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"AppException at {request.url.path}: {exc.message} | details={exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url.path),
        },
    )


async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "An unexpected internal error occurred. Please verify your input and try again.",
            "path": str(request.url.path),
        },
    )
