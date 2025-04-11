from collections.abc import AsyncGenerator
from typing import Any

from acp_sdk.models import (
    Await,
    AwaitResume,
    Message,
    TextMessagePart,
)
from acp_sdk.server import Context, Server

server = Server()


@server.agent()
async def awaiting(input: Message, context: Context) -> AsyncGenerator[Message | Await | Any, AwaitResume]:
    """Greets and awaits for more data"""
    yield Message(TextMessagePart(content="Hello!"))
    data = yield Await()
    yield Message(TextMessagePart(content=f"Thanks for {data}"))


server.run()
