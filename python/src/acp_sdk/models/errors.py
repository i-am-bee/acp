# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from enum import Enum

from pydantic import BaseModel


class ErrorCode(str, Enum):
    SERVER_ERROR = "server_error"
    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"


class Error(BaseModel):
    code: ErrorCode
    message: str


class ACPError(Exception):
    def __init__(self, error: Error) -> None:
        super().__init__()
        self.error = error

    def __str__(self) -> str:
        return str(self.error.message)
