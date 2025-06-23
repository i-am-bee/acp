# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio
from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

server = Server()


@server.agent()
async def echo(input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything, including session history"""
    async for message in context.session.load_history():
        yield message
    for message in input:
        await asyncio.sleep(0.5)
        yield {"thought": "I should echo everything"}
        await asyncio.sleep(0.5)
        yield message


server.run()
