import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from acp_sdk.server import Server
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_lifespan() -> None:
    entry = False
    exit = False

    class TestServer(Server):
        @asynccontextmanager
        async def lifespan(self, app: FastAPI) -> AsyncGenerator[None]:
            nonlocal entry
            nonlocal exit
            entry = True
            yield
            exit = True

    server = TestServer()
    task = asyncio.create_task(server.serve())
    await asyncio.sleep(1)
    server.should_exit = True
    await task

    assert entry
    assert exit
