from collections.abc import AsyncGenerator, Generator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import Agent, Context, RunYield, RunYieldResume, Server

server = Server()


@server.agent()
async def async_gen_echo(inputs: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    yield {"thought": "I should echo everyting"}
    yield input


@server.agent()
async def async_echo(inputs: list[Message], context: Context) -> RunYield:
    """Echoes everything"""
    await context.yield_async({"thought": "I should echo everyting"})
    return input


@server.agent()
def gen_echo(inputs: list[Message]) -> Generator[RunYield, RunYieldResume]:
    """Echoes everything"""
    yield {"thought": "I should echo everyting"}
    yield input


@server.agent()
def sync_echo(inputs: list[Message], context: Context) -> RunYield:
    """Echoes everything"""
    context.yield_sync({"thought": "I should echo everyting"})
    for message in inputs:
        yield message


class EchoAgent(Agent):
    @property
    def name(self) -> str:
        return "instance_echo"

    @property
    def description(self) -> str:
        return "Echoes everything"

    async def run(self, inputs: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
        """Echoes everything"""
        yield {"thought": "I should echo everyting"}
        for message in inputs:
            yield message


server.register(EchoAgent())


server.run()
