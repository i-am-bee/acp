import pytest
from acp_sdk.client.types import Input
from acp_sdk.client.utils import input_to_messages
from acp_sdk.models import Message, MessagePart


@pytest.mark.parametrize(
    "input,messages",
    [
        ([], []),
        ("Hello", [Message(parts=[MessagePart(content="Hello")])]),
        (["Hello"], [Message(parts=[MessagePart(content="Hello")])]),
        (MessagePart(content="Hello"), [Message(parts=[MessagePart(content="Hello")])]),
        ([MessagePart(content="Hello")], [Message(parts=[MessagePart(content="Hello")])]),
        (Message(parts=[MessagePart(content="Hello")]), [Message(parts=[MessagePart(content="Hello")])]),
        ([Message(parts=[MessagePart(content="Hello")])], [Message(parts=[MessagePart(content="Hello")])]),
    ],
)
def test_input_to_messages(input: Input, messages: list[Message]) -> None:
    result = input_to_messages(input)
    for r, m in zip(result, messages):
        assert r.parts == m.parts


@pytest.mark.parametrize(
    "input",
    [["foo", Message(parts=[])], ["foo", MessagePart(content="foo")], [Message(parts=[]), MessagePart(content="foo")]],
)
def test_input_to_messages_mixed_input(input: Input) -> None:
    with pytest.raises(TypeError):
        input_to_messages(["foo", Message(parts=[])])
