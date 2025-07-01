from enum import Enum
from typing import Optional

from pydantic import BaseModel

from acp_sdk.models.common import AnyModel


class ErrorCode(str, Enum):
    SERVER_ERROR = "server_error"
    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"


class Error(BaseModel):
    code: ErrorCode | str  # Allow arbitrary string for backwards compatibility
    message: str
    data: Optional[AnyModel] = None


class ACPError(Exception):
    def __init__(self, error: Error) -> None:
        super().__init__()
        self.error = error

    def __str__(self) -> str:
        return str(self.error.message)
