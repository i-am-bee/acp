import json
import uuid

import pytest
from acp_sdk.client import Client
from acp_sdk.models import (
    Agent,
    AgentsListResponse,
    Message,
    MessageAwaitResume,
    MessagePart,
    Run,
    RunCompletedEvent,
    RunEventsListResponse,
)
from pytest_httpx import HTTPXMock

mock_agent = Agent(name="mock")
mock_agents = [mock_agent]
mock_run = Run(
    agent_name=mock_agent.name, session_id=uuid.uuid4(), output=[Message(parts=[MessagePart(content="Hello!")])]
)


@pytest.mark.asyncio
async def test_agents(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://test/agents", method="GET", content=AgentsListResponse(agents=mock_agents).model_dump_json()
    )

    async with Client(base_url="http://test") as client:
        agents = [agent async for agent in client.agents()]
        assert agents == mock_agents


@pytest.mark.asyncio
async def test_agent(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"http://test/agents/{mock_agent.name}", method="GET", content=mock_agent.model_dump_json()
    )

    async with Client(base_url="http://test") as client:
        agent = await client.agent(name=mock_agent.name)
        assert agent == mock_agent


@pytest.mark.asyncio
async def test_run_sync(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://test/runs", method="POST", content=mock_run.model_dump_json())

    async with Client(base_url="http://test") as client:
        run = await client.run_sync("Howdy!", agent=mock_run.agent_name)
        assert run == mock_run


@pytest.mark.asyncio
async def test_run_async(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://test/runs", method="POST", content=mock_run.model_dump_json())

    async with Client(base_url="http://test") as client:
        run = await client.run_async("Howdy!", agent=mock_run.agent_name)
        assert run == mock_run


@pytest.mark.asyncio
async def test_run_stream(httpx_mock: HTTPXMock) -> None:
    mock_event = RunCompletedEvent(run=mock_run)
    httpx_mock.add_response(
        url="http://test/runs",
        method="POST",
        headers={"content-type": "text/event-stream"},
        content=f"data: {mock_event.model_dump_json()}\n\n",
    )

    async with Client(base_url="http://test") as client:
        async for event in client.run_stream("Howdy!", agent=mock_run.agent_name):
            assert event == mock_event


@pytest.mark.asyncio
async def test_run_status(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"http://test/runs/{mock_run.run_id}", method="GET", content=mock_run.model_dump_json())

    async with Client(base_url="http://test") as client:
        run = await client.run_status(run_id=mock_run.run_id)
        assert run == mock_run


@pytest.mark.asyncio
async def test_run_cancel(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"http://test/runs/{mock_run.run_id}/cancel", method="POST", content=mock_run.model_dump_json()
    )

    async with Client(base_url="http://test") as client:
        run = await client.run_cancel(run_id=mock_run.run_id)
        assert run == mock_run


@pytest.mark.asyncio
async def test_run_resume_sync(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"http://test/runs/{mock_run.run_id}", method="POST", content=mock_run.model_dump_json()
    )

    async with Client(base_url="http://test") as client:
        run = await client.run_resume_sync(MessageAwaitResume(message=Message(parts=[])), run_id=mock_run.run_id)
        assert run == mock_run


@pytest.mark.asyncio
async def test_run_resume_async(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"http://test/runs/{mock_run.run_id}", method="POST", content=mock_run.model_dump_json()
    )

    async with Client(base_url="http://test") as client:
        run = await client.run_resume_async(MessageAwaitResume(message=Message(parts=[])), run_id=mock_run.run_id)
        assert run == mock_run


@pytest.mark.asyncio
async def test_run_resume_stream(httpx_mock: HTTPXMock) -> None:
    mock_event = RunCompletedEvent(run=mock_run)
    httpx_mock.add_response(
        url=f"http://test/runs/{mock_run.run_id}",
        method="POST",
        headers={"content-type": "text/event-stream"},
        content=f"data: {mock_event.model_dump_json()}\n\n",
    )

    async with Client(base_url="http://test") as client:
        async for event in client.run_resume_stream(
            MessageAwaitResume(message=Message(parts=[])), run_id=mock_run.run_id
        ):
            assert event == mock_event


@pytest.mark.asyncio
async def test_run_events(httpx_mock: HTTPXMock) -> None:
    mock_event = RunCompletedEvent(run=mock_run)
    httpx_mock.add_response(
        url=f"http://test/runs/{mock_run.run_id}/events",
        method="GET",
        content=RunEventsListResponse(events=[mock_event]).model_dump_json(),
    )

    async with Client(base_url="http://test") as client:
        async for event in client.run_events(run_id=mock_run.run_id):
            assert event == mock_event


@pytest.mark.asyncio
async def test_session(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://test/runs", method="POST", content=mock_run.model_dump_json(), is_reusable=True)

    async with Client(base_url="http://test") as client, client.session(mock_run.session_id) as session:
        assert session._session_id == mock_run.session_id
        await session.run_sync("Howdy!", agent=mock_run.agent_name)
        await client.run_sync("Howdy!", agent=mock_run.agent_name)

    requests = httpx_mock.get_requests()
    body = json.loads(requests[0].content)
    assert body["session_id"] == str(mock_run.session_id)

    body = json.loads(requests[1].content)
    assert body["session_id"] is None


@pytest.mark.asyncio
async def test_no_session(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://test/runs", method="POST", content=mock_run.model_dump_json(), is_reusable=True)

    async with Client(base_url="http://test") as client:
        await client.run_sync("Howdy!", agent=mock_run.agent_name)
        await client.run_sync("Howdy!", agent=mock_run.agent_name)

    requests = httpx_mock.get_requests()

    body = json.loads(requests[1].content)
    assert body["session_id"] is None
