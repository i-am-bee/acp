from collections.abc import AsyncIterator

import pytest_asyncio
from acp_sdk.client import Client

from e2e.config import Config


@pytest_asyncio.fixture
async def client() -> AsyncIterator[Client]:
    async with Client(base_url=f"http://localhost:{Config.PORT}") as client:
        yield client
