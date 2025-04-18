import pytest
from acp_sdk.models.models import Message, MessagePart


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
