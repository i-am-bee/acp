from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

server = Server()


histories: dict[str, list[Message]] = {}


@server.agent(session=True)
async def historian(inputs: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes full session history"""
    assert context.session_id is not None

    history = histories.get(str(context.session_id), [])
    history.extend(inputs)
    for message in history:
        yield message
    histories[str(context.session_id)] = history


server.run()
