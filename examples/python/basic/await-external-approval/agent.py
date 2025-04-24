import asyncio
import random
import string
from collections.abc import AsyncGenerator

from acp_sdk import Message
from acp_sdk.models import MessageAwaitRequest, MessagePart
from acp_sdk.server import Context, Server

server = Server()


@server.agent()
async def approval_agent(inputs: list[Message], context: Context) -> AsyncGenerator:
    """Request approval and respond to user's confirmation."""

    # Pause execution and wait for external confirmation
    response = yield MessageAwaitRequest(
        message=Message(parts=[MessagePart(content="I can generate password for you. Do you want me to do that?")])
    )
    if str(response.message) == "yes":
        # User approved, continue execution
        yield MessagePart(content="Generating password...")
        # Simulate password generation
        await asyncio.sleep(1)
        yield Message(
            parts=[MessagePart(content=f"Your password is: {''.join(random.choices(string.ascii_letters, k=10))}")]
        )
    else:
        # User declined, stop execution
        yield MessagePart(content="Password generation declined.")


server.run()
