from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, status_code: int, name: str, message: str):
        self.status_code = status_code
        self.name = name
        self.message = message
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(status_code=404, name="NotFoundError", message=message)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(status_code=401, name="AuthenticationError", message=message)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(status_code=422, name="ValidationError", message=message)


def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.error(f"{exc.name}: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.name, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "InternalServerError", "message": "An unexpected error occurred"},
        )
