import time
from collections.abc import AsyncIterator, Generator
from threading import Thread

import pytest
import pytest_asyncio
from acp_sdk.client import Client
from acp_sdk.models import Await, AwaitResume, CompletedEvent, CreatedEvent, Message, RunStatus, TextMessagePart
from acp_sdk.models.models import InProgressEvent
from acp_sdk.server import Context, Server

PORT = 8000


@pytest.fixture
def server() -> Generator[None]:
    server = Server()

    @server.agent()
    async def echo(input: Message, context: Context):
        yield input

    @server.agent()
    async def awaiter(input: Message, context: Context):
        data = yield Await()
        yield Message(TextMessagePart(content="empty"))

    thread = Thread(target=server.run, kwargs={"port": PORT}, daemon=True)
    thread.start()

    time.sleep(1)

    yield

    server.should_exit = True
    thread.join(timeout=2)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[Client]:
    async with Client(base_url=f"http://localhost:{PORT}") as client:
        yield client


@pytest.mark.asyncio
async def test_run_sync(server: Server, client: Client) -> None:
    input = Message(TextMessagePart(content="Hello!"))
    run = await client.run_sync(agent="echo", input=input)
    assert run.status == RunStatus.COMPLETED
    assert run.output == input


@pytest.mark.asyncio
async def test_run_async(server: Server, client: Client) -> None:
    input = Message(TextMessagePart(content="Hello!"))
    run = await client.run_async(agent="echo", input=input)
    assert run.status == RunStatus.CREATED
    assert run.output is None


@pytest.mark.asyncio
async def test_run_stream(server: Server, client: Client) -> None:
    input = Message(TextMessagePart(content="Hello!"))
    event_stream = [event async for event in client.run_stream(agent="echo", input=input)]
    assert isinstance(event_stream[0], CreatedEvent)
    assert isinstance(event_stream[-1], CompletedEvent)


@pytest.mark.asyncio
async def test_run_status(server: Server, client: Client) -> None:
    input = Message(TextMessagePart(content="Hello!"))
    run = await client.run_async(agent="echo", input=input)
    while run.status in (RunStatus.CREATED, RunStatus.IN_PROGRESS):
        run = await client.run_status(run_id=run.run_id)
    assert run.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_run_resume_sync(server: Server, client: Client) -> None:
    input = Message(TextMessagePart(content="Hello!"))

    run = await client.run_sync(agent="awaiter", input=input)
    assert run.status == RunStatus.AWAITING
    assert run.await_ is not None

    run = await client.run_resume_sync(run_id=run.run_id, await_=AwaitResume())
    assert run.status == RunStatus.COMPLETED
    assert run.output is not None


@pytest.mark.asyncio
async def test_run_resume_async(server: Server, client: Client) -> None:
    input = Message(TextMessagePart(content="Hello!"))

    run = await client.run_sync(agent="awaiter", input=input)
    assert run.status == RunStatus.AWAITING
    assert run.await_ is not None

    run = await client.run_resume_async(run_id=run.run_id, await_=AwaitResume())
    assert run.status == RunStatus.AWAITING


@pytest.mark.asyncio
async def test_run_resume_stream(server: Server, client: Client) -> None:
    input = Message(TextMessagePart(content="Hello!"))

    run = await client.run_sync(agent="awaiter", input=input)
    assert run.status == RunStatus.AWAITING
    assert run.await_ is not None

    event_stream = [event async for event in client.run_resume_stream(run_id=run.run_id, await_=AwaitResume())]
    assert isinstance(event_stream[0], InProgressEvent)
    assert isinstance(event_stream[-1], CompletedEvent)
