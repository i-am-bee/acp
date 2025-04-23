from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from acp_sdk.models import Error, ErrorCode
from acp_sdk.models.errors import ACPError
from acp_sdk.server.logging import logger


def error_code_to_status_code(error_code: ErrorCode) -> int:
    match error_code:
        case ErrorCode.NOT_FOUND:
            return status.HTTP_404_NOT_FOUND
        case ErrorCode.INVALID_INPUT:
            return status.HTTP_422_UNPROCESSABLE_ENTITY
        case _:
            return status.HTTP_500_INTERNAL_SERVER_ERROR


def status_code_to_error_code(status_code: int) -> ErrorCode:
    match status_code:
        case status.HTTP_400_BAD_REQUEST:
            return ErrorCode.INVALID_INPUT
        case status.HTTP_404_NOT_FOUND:
            return ErrorCode.NOT_FOUND
        case status.HTTP_422_UNPROCESSABLE_ENTITY:
            return ErrorCode.INVALID_INPUT
        case _:
            return ErrorCode.SERVER_ERROR


async def acp_error_handler(request: Request, exc: ACPError, *, status_code: int | None = None) -> JSONResponse:
    error = exc.error
    return JSONResponse(
        status_code=status_code or error_code_to_status_code(error.code), content=error.model_dump(mode="json")
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return await acp_error_handler(
        request,
        ACPError(Error(code=status_code_to_error_code(exc.status_code), message=exc.detail)),
        status_code=exc.status_code,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return await acp_error_handler(request, ACPError(Error(code=ErrorCode.INVALID_INPUT, message=str(exc))))


async def catch_all_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(exc)
    return await acp_error_handler(
        request, ACPError(Error(code=ErrorCode.SERVER_ERROR, message="An unexpected error occurred"))
    )
