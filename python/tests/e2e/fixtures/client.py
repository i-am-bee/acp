from collections.abc import AsyncIterator

import pytest_asyncio
from acp_sdk.client import Client

PORT = 8000


@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncIterator[Client]:
    async with Client(base_url=f"http://localhost:{PORT}") as client:
        yield client
