from collections.abc import AsyncGenerator

from acp_sdk import Message
from acp_sdk.models import AwaitRequest, MessagePart
from acp_sdk.server import Context, Server

server = Server()


@server.agent()
async def approval_agent(inputs: list[Message], context: Context) -> AsyncGenerator:
    """Request approval and respond to user's confirmation."""
    yield MessagePart(content="Hello! I need an approval.")

    # Pause execution and wait for external confirmation
    yield AwaitRequest()

    yield MessagePart(content="Thank you for approving!")


server.run()
