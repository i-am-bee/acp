from collections.abc import AsyncGenerator
from acp_sdk.models import AwaitRequest, MessagePart
from acp_sdk.server import Context, Server

server = Server()


@server.agent()
async def approval_agent(inputs: list[MessagePart], context: Context) -> AsyncGenerator:
    """Request approval and respond to user's confirmation."""
    yield MessagePart(content="Hello! I need an approval.", content_type="text/plain")

    # Pause execution and wait for external confirmation
    yield AwaitRequest()

    yield MessagePart(content="Thank you for approving!", content_type="text/plain")


server.run()
