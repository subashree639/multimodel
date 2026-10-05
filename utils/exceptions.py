from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import logging
import time

logger = logging.getLogger(__name__)


class CustomException(Exception):
    def __init__(self, name: str, message: str, status_code: int = 400):
        self.name = name
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(CustomException):
    def __init__(self, message: str):
        super().__init__("ValidationError", message, status_code=422)


class AuthenticationError(CustomException):
    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__("AuthenticationError", message, status_code=401)


class NotFoundError(CustomException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__("NotFoundError", message, status_code=404)


def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        logger.error(f"Custom exception: {exc.name} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.name,
                "message": exc.message,
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "path": str(request.url.path),
            },
        )

