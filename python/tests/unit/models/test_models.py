import pytest
from acp_sdk.models.models import Message, MessagePart


@pytest.mark.parametrize(
    "first,second,result",
    [
        (
            Message(parts=[MessagePart(content_type="text/plain", content="Foo")]),
            Message(parts=[MessagePart(content_type="text/plain", content="Bar")]),
            Message(
                parts=[
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/plain", content="Bar"),
                ]
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
                ]
            ),
            Message(parts=[MessagePart(content_type="text/plain", content="FooBar")]),
        ),
        (
            Message(
                parts=[
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/html", content="<head>"),
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/plain", content="Bar"),
                ]
            ),
            Message(
                parts=[
                    MessagePart(content_type="text/plain", content="Foo"),
                    MessagePart(content_type="text/html", content="<head>"),
                    MessagePart(content_type="text/plain", content="FooBar"),
                ]
            ),
        ),
    ],
)
def test_message_compress(uncompressed: Message, compressed: Message) -> None:
    assert uncompressed.compress() == compressed
