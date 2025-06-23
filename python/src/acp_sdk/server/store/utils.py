# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from typing import Protocol


class Stringable(Protocol):
    def __str__(self) -> str: ...
