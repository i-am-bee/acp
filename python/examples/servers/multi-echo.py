from collections.abc import AsyncGenerator, Generator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

# This example showcases several ways to create echo agent using decoratos.

server = Server()


@server.agent(description="Async generator")
async def async_gen_echo(input: Message, context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    yield {"thought": "I should echo everyting"}
    yield input


@server.agent(description="Async")
async def async_echo(input: Message, context: Context) -> RunYield:
    """Echoes everything"""
    await context.yield_async({"thought": "I should echo everyting"})
    return input


@server.agent(description="Generator")
def gen_echo(input: Message, context: Context) -> Generator[RunYield, RunYieldResume]:
    """Echoes everything"""
    yield {"thought": "I should echo everyting"}
    return input


@server.agent(description="Sync")
def sync_echo(input: Message, context: Context) -> RunYield:
    """Echoes everything"""
    context.yield_sync({"thought": "I should echo everyting"})
    return input


server.run()
