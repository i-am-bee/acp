import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from acp_sdk.models import (
    Await,
    AwaitResume,
    Message,
)
from acp_sdk.server import Context, Server

server = Server()


@server.agent()
async def echo(input: Message, context: Context) -> AsyncGenerator[Message | Await | Any, AwaitResume]:
    """Echoes everything"""
    for part in input:
        await asyncio.sleep(0.5)
        yield {"thought": "I should echo everyting"}
        yield Message(part)


server.run()
