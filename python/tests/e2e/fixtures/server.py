import time
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from threading import Thread

import pytest
from acp_sdk.models import Await, AwaitResume, Message, MessagePart
from acp_sdk.server import Context, Server

from e2e.config import Config


@pytest.fixture(scope="module")
def server() -> Generator[None]:
    server = Server()

    @server.agent()
    async def echo(inputs: list[Message], context: Context) -> AsyncIterator[Message]:
        for message in inputs:
            yield message

    @server.agent()
    async def awaiter(inputs: list[Message], context: Context) -> AsyncGenerator[Message | Await, AwaitResume]:
        yield Await()
        yield Message(MessagePart(content="empty", content_type="text/plain"))

    @server.agent()
    async def failer(inputs: list[Message], context: Context) -> AsyncIterator[Message]:
        raise RuntimeError("Whoops")

    thread = Thread(target=server.run, kwargs={"port": Config.PORT}, daemon=True)
    thread.start()

    time.sleep(1)

    yield server

    server.should_exit = True
    thread.join(timeout=2)
