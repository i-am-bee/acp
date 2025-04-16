from collections.abc import AsyncGenerator
from typing import Any

from acp_sdk.models import (
    Await,
    AwaitResume,
    Message,
    MessagePart,
)
from acp_sdk.server import Context, Server

server = Server()


@server.agent()
async def awaiting(inputs: list[Message], context: Context) -> AsyncGenerator[Message | Await | Any, AwaitResume]:
    """Greets and awaits for more data"""
    yield Message(MessagePart(content="Hello!", content_type="text/plain"))
    data = yield Await()
    yield Message(MessagePart(content=f"Thanks for {data}", content_type="text/plain"))


server.run()
