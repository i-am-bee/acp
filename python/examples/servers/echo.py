import asyncio
from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Await,
    AwaitResume,
    Message,
)
from acp_sdk.server import Agent, serve
from acp_sdk.server.context import Context


class EchoAgent(Agent):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes everything"

    async def run(self, input: Message, *, context: Context) -> AsyncGenerator[Message | Await, AwaitResume]:
        for part in input:
            await asyncio.sleep(0.5)
            yield {"thought": "I should echo everyting"}
            yield Message(part)


serve(EchoAgent())
