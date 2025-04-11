from acp_sdk.models import (
    Message,
)
from acp_sdk.server import RunYield, Server, SyncContext

server = Server()


@server.agent()
def echo(input: Message, context: SyncContext) -> RunYield:
    """Echoes everything"""
    context.yield_({"thought": "I should echo everyting"})
    return input


server.run()
