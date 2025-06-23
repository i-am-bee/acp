# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
    MessageAwaitRequest,
    MessageAwaitResume,
    MessagePart,
)
from acp_sdk.server import Context, Server
from acp_sdk.server.types import RunYield, RunYieldResume

server = Server()


@server.agent()
async def awaiting(input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Greets and awaits for more data"""
    yield MessagePart(content="Hello!")
    resume = yield MessageAwaitRequest(
        message=Message(parts=[MessagePart(content="Can you provide me with additional configuration?")])
    )
    assert isinstance(resume, MessageAwaitResume)
    yield MessagePart(content=f"Thanks for config: {resume.message}")


server.run()
