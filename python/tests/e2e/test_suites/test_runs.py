import pytest
from acp_sdk.client import Client
from acp_sdk.models import AwaitResume, CompletedEvent, CreatedEvent, Message, RunStatus, TextMessagePart
from acp_sdk.models.models import InProgressEvent
from acp_sdk.server import Server

input = Message(TextMessagePart(content="Hello!"))


@pytest.mark.asyncio
async def test_run_sync(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="echo", input=input)
    assert run.status == RunStatus.COMPLETED
    assert run.output == input


@pytest.mark.asyncio
async def test_run_async(server: Server, client: Client) -> None:
    run = await client.run_async(agent="echo", input=input)
    assert run.status == RunStatus.CREATED
    assert run.output is None


@pytest.mark.asyncio
async def test_run_stream(server: Server, client: Client) -> None:
    event_stream = [event async for event in client.run_stream(agent="echo", input=input)]
    assert isinstance(event_stream[0], CreatedEvent)
    assert isinstance(event_stream[-1], CompletedEvent)


@pytest.mark.asyncio
async def test_run_status(server: Server, client: Client) -> None:
    run = await client.run_async(agent="echo", input=input)
    while run.status in (RunStatus.CREATED, RunStatus.IN_PROGRESS):
        run = await client.run_status(run_id=run.run_id)
    assert run.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_failure(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="failer", input=input)
    assert run.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_run_cancel(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="awaiter", input=input)
    assert run.status == RunStatus.AWAITING
    run = await client.run_cancel(run_id=run.run_id)
    assert run.status == RunStatus.CANCELLING


@pytest.mark.asyncio
async def test_run_resume_sync(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="awaiter", input=input)
    assert run.status == RunStatus.AWAITING
    assert run.await_ is not None

    run = await client.run_resume_sync(run_id=run.run_id, await_=AwaitResume())
    assert run.status == RunStatus.COMPLETED
    assert run.output is not None


@pytest.mark.asyncio
async def test_run_resume_async(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="awaiter", input=input)
    assert run.status == RunStatus.AWAITING
    assert run.await_ is not None

    run = await client.run_resume_async(run_id=run.run_id, await_=AwaitResume())
    assert run.status == RunStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_run_resume_stream(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="awaiter", input=input)
    assert run.status == RunStatus.AWAITING
    assert run.await_ is not None

    event_stream = [event async for event in client.run_resume_stream(run_id=run.run_id, await_=AwaitResume())]
    assert isinstance(event_stream[0], InProgressEvent)
    assert isinstance(event_stream[-1], CompletedEvent)


@pytest.mark.asyncio
async def test_run_session(server: Server, client: Client) -> None:
    async with client.session() as session:
        run = await session.run_sync(agent="sessioner", input=input)
        session_id = run.session_id
        run = await session.run_sync(agent="sessioner", input=input)
        assert session_id == run.session_id
