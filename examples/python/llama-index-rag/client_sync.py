# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio

from acp_sdk.client import Client
from acp_sdk.models import (
    Message,
    MessagePart,
)


async def client() -> None:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(agent="llamaindex_rag_agent", input="What is Docling?")
        print(run.output[-1])


if __name__ == "__main__":
    asyncio.run(client())
