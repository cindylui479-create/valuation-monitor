from enum import Enum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    DATA_SOURCE_UNAVAILABLE = "DATA_SOURCE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


_HTTP_STATUS = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.BUSINESS_RULE_VIOLATION: 400,
    ErrorCode.DATA_SOURCE_UNAVAILABLE: 503,
    ErrorCode.INTERNAL_ERROR: 500,
}


class AppException(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    @property
    def status_code(self) -> int:
        return _HTTP_STATUS[self.code]

    def to_payload(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
            }
        }


class NotFound(AppException):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(ErrorCode.NOT_FOUND, message, details)


class BusinessRuleViolation(AppException):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(ErrorCode.BUSINESS_RULE_VIOLATION, message, details)


class DataSourceUnavailable(AppException):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(ErrorCode.DATA_SOURCE_UNAVAILABLE, message, details)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _app_exc(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def _val_exc(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic 自定义校验器抛出的 ValueError 会带进 ctx.error，需要剥离以可 JSON 序列化
        clean_errors: list[dict[str, Any]] = []
        for err in exc.errors():
            e = dict(err)
            ctx = e.get("ctx")
            if isinstance(ctx, dict):
                e["ctx"] = {
                    k: (str(v) if isinstance(v, Exception) else v) for k, v in ctx.items()
                }
            clean_errors.append(e)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "Request validation failed",
                    "details": {"errors": clean_errors},
                }
            },
        )

    @app.exception_handler(Exception)
    async def _generic_exc(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": str(exc),
                    "details": {},
                }
            },
        )
