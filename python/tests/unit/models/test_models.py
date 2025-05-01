import asyncio

import pytest
from acp_sdk.models.errors import ACPError, Error, ErrorCode
from acp_sdk.models.models import Message, MessagePart, Run, RunStatus

timestamp = "2021-09-09T22:02:47.89Z"


@pytest.mark.parametrize(
    "first,second,result",
    [
        (
            Message(
                parts=[MessagePart(content_type="text/plain", content="Foo")],
                created_at=timestamp,
                completed_at=timestamp,
            ),
            Message(
                parts=[MessagePart(content_type="text/plain", content="Bar")],
                created_at=timestamp,
                completed_at=timestamp,
            ),
            Message(
                parts=[
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/plain", content="Bar"),
                ],
                created_at=timestamp,
                completed_at=timestamp,
            ),
        ),
        (
            Message(
                parts=[MessagePart(content_type="text/plain", content="Foo")],
                created_at=None,
                completed_at=timestamp,
            ),
            Message(
                parts=[MessagePart(content_type="text/plain", content="Bar")],
                created_at=timestamp,
                completed_at=None,
            ),
            Message(
                parts=[
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/plain", content="Bar"),
                ],
                created_at=None,
                completed_at=None,
            ),
        ),
    ],
)
def test_message_add(first: Message, second: Message, result: Message) -> None:
    assert first + second == result


@pytest.mark.parametrize(
    "uncompressed,compressed",
    [
        (
            Message(
                parts=[
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/plain", content="Bar"),
                ],
                created_at=timestamp,
                completed_at=timestamp,
            ),
            Message(
                parts=[MessagePart(content_type="text/plain", content="FooBar")],
                created_at=timestamp,
                completed_at=timestamp,
            ),
        ),
        (
            Message(
                parts=[
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/html", content="<head>"),
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/plain", content="Bar"),
                ],
                created_at=timestamp,
                completed_at=timestamp,
            ),
            Message(
                parts=[
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/html", content="<head>"),
                    MessagePart(content_type="text/plain", content="FooBar"),
                ],
                created_at=timestamp,
                completed_at=timestamp,
            ),
        ),
    ],
)
def test_message_compress(uncompressed: Message, compressed: Message) -> None:
    assert uncompressed.compress() == compressed


@pytest.mark.parametrize(
    "run,error",
    [
        (
            Run(agent_name="foo", status=RunStatus.CANCELLED),
            asyncio.CancelledError,
        ),
        (
            Run(
                agent_name="foo",
                status=RunStatus.FAILED,
                error=Error(code=ErrorCode.SERVER_ERROR, message="Unspecified"),
            ),
            ACPError,
        ),
        (
            Run(agent_name="foo"),
            None,
        ),
        (
            Run(agent_name="foo", status=RunStatus.IN_PROGRESS),
            None,
        ),
        (
            Run(agent_name="foo", status=RunStatus.COMPLETED),
            None,
        ),
    ],
)
def test_run_raise_on_status_raise(run: Run, error: type[Exception] | None) -> None:
    if error:
        with pytest.raises(error):
            run.raise_for_status()
    else:
        run.raise_for_status()
