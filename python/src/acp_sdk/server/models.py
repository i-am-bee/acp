# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio
from collections.abc import AsyncIterator
from typing import Self

from pydantic import BaseModel

from acp_sdk.models import (
    Event,
    Run,
)
from acp_sdk.server.store import Store


class RunData(BaseModel):
    run: Run
    events: list[Event] = []

    @property
    def key(self) -> str:
        return str(self.run.run_id)

    async def watch(self, store: Store[Self], *, ready: asyncio.Event | None = None) -> AsyncIterator[Self]:
        async for data in store.watch(self.key, ready=ready):
            if data is None:
                raise RuntimeError("Missing data")
            yield data
            if data.run.status.is_terminal:
                break


class CancelData(BaseModel):
    pass
