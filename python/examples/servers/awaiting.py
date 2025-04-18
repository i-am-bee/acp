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
async def awaiting(inputs: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Greets and awaits for more data"""
    yield MessagePart(content="Hello!", content_type="text/plain")
    resume = yield MessageAwaitRequest(
        message=Message(
            parts=[MessagePart(content="Can you provide me with additional configuration?", content_type="text/plain")]
        )
    )
    assert isinstance(resume, MessageAwaitResume)
    yield MessagePart(content=f"Thanks for config: {resume.message}", content_type="text/plain")


server.run()
