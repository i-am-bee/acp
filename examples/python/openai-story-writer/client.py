# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart

import asyncio


async def run_agent(agent: str, input: str) -> list[Message]:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(agent=agent, input=input)
    return run.output


if __name__ == "__main__":
    response = asyncio.run(run_agent("story_writer", "Write a sci-fi story"))
    print(response)
