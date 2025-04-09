from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Await,
    AwaitResume,
    Message,
    TextMessagePart,
)
from acp_sdk.server import Agent, serve
from acp_sdk.server.context import Context


class AwaitingAgent(Agent):
    @property
    def name(self) -> str:
        return "awaiting"

    @property
    def description(self) -> str:
        return "Greets and awaits for more data"

    async def run(self, input: Message, *, context: Context) -> AsyncGenerator[Message | Await, AwaitResume]:
        yield Message(TextMessagePart(content="Hello!"))
        data = yield Await()
        yield Message(TextMessagePart(content=f"Thanks for {data}"))


serve(AwaitingAgent())
