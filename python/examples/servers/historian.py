from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.models.models import SessionId
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

server = Server()


histories: dict[str, list[Message]] = {}


@server.agent(session=True)
async def historian(input: Message, context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes full session history"""
    assert context.session_id is not None

    history = histories.get(str(context.session_id), [])
    history.append(input)
    for message in history:
        yield message
    histories[str(context.session_id)] = history


server.run()
