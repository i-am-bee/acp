import json

import pytest
from acp_sdk.client import Client
from acp_sdk.models import (
    ACPError,
    AgentManifest,
    AgentsListResponse,
    Error,
    ErrorCode,
    ErrorEvent,
    Message,
    MessageAwaitResume,
    MessagePart,
    Run,
    RunCompletedEvent,
    RunEventsListResponse,
    Session,
)
from pytest_httpx import HTTPXMock

mock_agent = AgentManifest(name="mock", input_content_types=[], output_content_types=[])
mock_agents = [mock_agent]
mock_session = Session()
mock_run = Run(
    agent_name=mock_agent.name, session_id=mock_session.id, output=[Message(parts=[MessagePart(content="Hello!")])]
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
async def test_run_stream_error(httpx_mock: HTTPXMock) -> None:
    error = Error(code=ErrorCode.SERVER_ERROR, message="whoops")
    mock_event = ErrorEvent(error=error)
    httpx_mock.add_response(
        url="http://test/runs",
        method="POST",
        headers={"content-type": "text/event-stream"},
        content=f"data: {mock_event.model_dump_json()}\n\n",
    )

    async with Client(base_url="http://test") as client:
        with pytest.raises(ACPError) as e:
            async for _ in client.run_stream("Howdy!", agent=mock_run.agent_name):
                raise AssertionError()
        assert e.value.error == error


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
    httpx_mock.add_response(
        url=f"http://test/sessions/{mock_session.id}",
        method="GET",
        content=mock_session.model_dump_json(),
        is_reusable=True,
    )

    async with Client(base_url="http://test") as client, client.session(mock_session) as session:
        await session.run_sync("Howdy!", agent=mock_run.agent_name)
        await session.run_sync("Howdy!", agent=mock_run.agent_name)
        await client.run_sync("Howdy!", agent=mock_run.agent_name)

    requests = httpx_mock.get_requests()
    body = json.loads(requests[1].content)
    # First request gets full session
    assert body["session"]["id"] == str(mock_run.session_id)

    body = json.loads(requests[2].content)
    # Second sends just the ID
    assert body["session_id"] == str(mock_run.session_id)

    body = json.loads(requests[3].content)
    assert body["session_id"] is None
    assert body["session"] is None


@pytest.mark.asyncio
async def test_no_session(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://test/runs", method="POST", content=mock_run.model_dump_json(), is_reusable=True)

    async with Client(base_url="http://test") as client:
        await client.run_sync("Howdy!", agent=mock_run.agent_name)
        await client.run_sync("Howdy!", agent=mock_run.agent_name)

    requests = httpx_mock.get_requests()

    body = json.loads(requests[1].content)
    assert body["session_id"] is None


@pytest.mark.asyncio
async def test_distributed_session(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://one/runs", method="POST", content=mock_run.model_dump_json())
    httpx_mock.add_response(
        url=f"http://one/sessions/{mock_session.id}",
        method="GET",
        content=mock_session.model_dump_json(),
        is_reusable=True,
    )
    httpx_mock.add_response(url="http://two/runs", method="POST", content=mock_run.model_dump_json())

    async with Client() as client, client.session(mock_session) as session:
        await session.run_sync("Howdy!", agent=mock_run.agent_name, base_url="http://one")
        await session.run_sync("Howdy!", agent=mock_run.agent_name, base_url="http://two")


@pytest.mark.asyncio
async def test_create_url() -> None:
    async with Client(base_url="http://test") as client:
        assert str(client._create_url("/agents", base_url=None)) == "http://test/agents"
        assert str(client._create_url("/agents", base_url="http://foo")) == "http://foo/agents"
        assert str(client._create_url("/agents", base_url="http://foo/")) == "http://foo/agents"
        assert str(client._create_url("/agents", base_url="http://foo/bar")) == "http://foo/bar/agents"
        assert str(client._create_url("/agents", base_url="http://foo/bar/")) == "http://foo/bar/agents"
        assert str(client._create_url("/agents", base_url="/foo")) == "/foo/agents"
