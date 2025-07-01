# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio

from acp_sdk import MessagePartEvent
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart


async def client() -> None:
    async with Client(base_url="http://localhost:8000") as client:
        async for event in client.run_stream(
            agent="gpt_researcher",
            input=[Message(parts=[MessagePart(content="Protocols focused on agent to agent communication")])],
        ):
            match event:
                case MessagePartEvent():
                    print(event.part.content)


if __name__ == "__main__":
    asyncio.run(client())
