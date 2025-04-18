import base64

import pytest
from acp_sdk.client import Client
from acp_sdk.models import (
    ArtifactEvent,
    ErrorCode,
    Message,
    MessageAwaitResume,
    MessageCreatedEvent,
    MessagePart,
    RunCompletedEvent,
    RunCreatedEvent,
    RunInProgressEvent,
    RunStatus,
)
from acp_sdk.server import Server

inputs = [Message(parts=[MessagePart(content="Hello!")])]
await_resume = MessageAwaitResume(message=Message(parts=[]))


@pytest.mark.asyncio
async def test_run_sync(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="echo", inputs=inputs)
    assert run.status == RunStatus.COMPLETED
    assert run.outputs == inputs


@pytest.mark.asyncio
async def test_run_async(server: Server, client: Client) -> None:
    run = await client.run_async(agent="echo", inputs=inputs)
    assert run.status == RunStatus.CREATED


@pytest.mark.asyncio
async def test_run_stream(server: Server, client: Client) -> None:
    event_stream = [event async for event in client.run_stream(agent="echo", inputs=inputs)]
    assert isinstance(event_stream[0], RunCreatedEvent)
    assert isinstance(event_stream[-1], RunCompletedEvent)


@pytest.mark.asyncio
async def test_run_status(server: Server, client: Client) -> None:
    run = await client.run_async(agent="echo", inputs=inputs)
    while run.status in (RunStatus.CREATED, RunStatus.IN_PROGRESS):
        run = await client.run_status(run_id=run.run_id)
    assert run.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_failure(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="failer", inputs=inputs)
    assert run.status == RunStatus.FAILED
    assert run.error is not None
    assert run.error.code == ErrorCode.INVALID_INPUT


@pytest.mark.asyncio
async def test_run_cancel(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="awaiter", inputs=inputs)
    assert run.status == RunStatus.AWAITING
    run = await client.run_cancel(run_id=run.run_id)
    assert run.status == RunStatus.CANCELLING


@pytest.mark.asyncio
async def test_run_resume_sync(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="awaiter", inputs=inputs)
    assert run.status == RunStatus.AWAITING
    assert run.await_request is not None

    run = await client.run_resume_sync(run_id=run.run_id, await_resume=await_resume)
    assert run.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_run_resume_async(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="awaiter", inputs=inputs)
    assert run.status == RunStatus.AWAITING
    assert run.await_request is not None

    run = await client.run_resume_async(run_id=run.run_id, await_resume=await_resume)
    assert run.status == RunStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_run_resume_stream(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="awaiter", inputs=inputs)
    assert run.status == RunStatus.AWAITING
    assert run.await_request is not None

    event_stream = [event async for event in client.run_resume_stream(run_id=run.run_id, await_resume=await_resume)]
    assert isinstance(event_stream[0], RunInProgressEvent)
    assert isinstance(event_stream[-1], RunCompletedEvent)


@pytest.mark.asyncio
async def test_run_session(server: Server, client: Client) -> None:
    async with client.session() as session:
        run = await session.run_sync(agent="echo", inputs=inputs)
        assert run.outputs == inputs
        run = await session.run_sync(agent="echo", inputs=inputs)
        assert run.outputs == inputs + inputs + inputs


@pytest.mark.asyncio
async def test_mime_types(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="mime_types", inputs=inputs)
    assert run.status == RunStatus.COMPLETED
    assert len(run.outputs) == 1

    message_parts = run.outputs[0].parts
    content_types = [part.content_type for part in message_parts]

    assert "text/html" in content_types
    assert "application/json" in content_types
    assert "application/javascript" in content_types
    assert "text/css" in content_types

    for part in message_parts:
        if part.content_type == "text/html":
            assert part.content == "<h1>HTML Content</h1>"
        elif part.content_type == "application/json":
            assert part.content == '{"key": "value"}'


@pytest.mark.asyncio
async def test_base64_encoding(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="base64_encoding", inputs=inputs)
    assert run.status == RunStatus.COMPLETED
    assert len(run.outputs) == 1

    message_parts = run.outputs[0].parts
    assert len(message_parts) == 2

    base64_part = next((part for part in message_parts if part.content_encoding == "base64"), None)
    assert base64_part is not None
    assert base64_part.content_type == "image/png"
    assert base64_part.content is not None

    text_part = next((part for part in message_parts if part.content_type == "text/plain"), None)
    assert text_part is not None
    assert text_part.content == "This is plain text"
    assert text_part.content_encoding == "plain"


@pytest.mark.asyncio
async def test_artifacts(server: Server, client: Client) -> None:
    run = await client.run_sync(agent="artifact_producer", inputs=inputs)
    assert run.status == RunStatus.COMPLETED

    assert len(run.outputs) == 1
    assert run.outputs[0].parts[0].content == "Processing with artifacts"

    assert len(run.outputs[0].parts) == 4

    text_artifact = next((a for a in run.outputs[0].parts if a.name == "text-result.txt"), None)
    json_artifact = next((a for a in run.outputs[0].parts if a.name == "data.json"), None)
    image_artifact = next((a for a in run.outputs[0].parts if a.name == "image.png"), None)

    assert text_artifact is not None
    assert text_artifact.content_type == "text/plain"
    assert text_artifact.content == "This is a text artifact result"
    assert text_artifact.content_encoding == "plain"

    assert json_artifact is not None
    assert json_artifact.content_type == "application/json"
    assert json_artifact.content == '{"results": [1, 2, 3], "status": "complete"}'

    assert image_artifact is not None
    assert image_artifact.content_type == "image/png"
    assert image_artifact.content_encoding == "base64"
    base64.b64decode(image_artifact.content)


@pytest.mark.asyncio
async def test_artifact_streaming(server: Server, client: Client) -> None:
    events = [event async for event in client.run_stream(agent="artifact_producer", inputs=inputs)]

    assert isinstance(events[0], RunCreatedEvent)
    assert isinstance(events[-1], RunCompletedEvent)

    message_events = [e for e in events if isinstance(e, MessageCreatedEvent)]
    artifact_events = [e for e in events if isinstance(e, ArtifactEvent)]

    assert len(message_events) == 1
    assert message_events[0].message.parts[0].content == "Processing with artifacts"

    assert len(artifact_events) == 3

    artifact_types = [a.part.content_type for a in artifact_events]
    assert "text/plain" in artifact_types
    assert "application/json" in artifact_types
    assert "image/png" in artifact_types
