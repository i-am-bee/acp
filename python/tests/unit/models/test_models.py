import pytest
from acp_sdk.models.models import Message, MessagePart

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
        )
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
