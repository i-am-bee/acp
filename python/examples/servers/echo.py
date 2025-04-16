import asyncio
from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

server = Server()


@server.agent()
async def echo(inputs: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in inputs:
        await asyncio.sleep(0.5)
        yield {"thought": "I should echo everyting"}
        await asyncio.sleep(0.5)
        yield message


server.run()
