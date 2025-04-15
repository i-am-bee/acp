import time
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from threading import Thread

import pytest
from acp_sdk.models import Await, AwaitResume, Message, TextMessagePart
from acp_sdk.server import Context, Server

PORT = 8000


@pytest.fixture(scope="session")
def server() -> Generator[None]:
    server = Server()

    @server.agent()
    async def echo(input: Message, context: Context) -> AsyncIterator[Message]:
        yield input

    @server.agent()
    async def awaiter(input: Message, context: Context) -> AsyncGenerator[Message | Await, AwaitResume]:
        yield Await()
        yield Message(TextMessagePart(content="empty"))

    thread = Thread(target=server.run, kwargs={"port": PORT}, daemon=True)
    thread.start()

    time.sleep(1)

    yield server

    server.should_exit = True
    thread.join(timeout=2)
