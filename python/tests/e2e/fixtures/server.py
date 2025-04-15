import time
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from threading import Thread

import pytest
from acp_sdk.models import Await, AwaitResume, Message, TextMessagePart
from acp_sdk.server import Context, Server

from e2e.config import Config


@pytest.fixture(scope="module")
def server() -> Generator[None]:
    server = Server()

    @server.agent()
    async def echo(input: Message, context: Context) -> AsyncIterator[Message]:
        yield input

    @server.agent()
    async def awaiter(input: Message, context: Context) -> AsyncGenerator[Message | Await, AwaitResume]:
        yield Await()
        yield Message(TextMessagePart(content="empty"))

    thread = Thread(target=server.run, kwargs={"port": Config.PORT}, daemon=True)
    thread.start()

    time.sleep(1)

    yield server

    server.should_exit = True
    thread.join(timeout=2)
