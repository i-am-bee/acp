import pytest
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart, Run, RunCompletedEvent
from pytest_httpx import HTTPXMock

mock_run = Run(agent_name="mock", outputs=[Message(parts=[MessagePart(content="Hello!")])])


@pytest.mark.asyncio
async def test_run_sync(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(content=mock_run.model_dump_json())

    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync("Howdy!", agent="mock")
        assert run == mock_run


@pytest.mark.asyncio
async def test_run_async(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(content=mock_run.model_dump_json())

    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_async("Howdy!", agent="mock")
        assert run == mock_run


@pytest.mark.asyncio
async def test_run_stream(httpx_mock: HTTPXMock) -> None:
    mock_event = RunCompletedEvent(run=mock_run)
    httpx_mock.add_response(
        headers={"content-type": "text/event-stream"}, content=f"data: {mock_event.model_dump_json()}\n\n"
    )

    async with Client(base_url="http://localhost:8000") as client:
        async for event in client.run_stream("Howdy!", agent="mock"):
            assert event == mock_event
