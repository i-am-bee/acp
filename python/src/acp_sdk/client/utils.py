from acp_sdk.client.types import Input
from acp_sdk.models.models import Message, MessagePart


def input_to_messages(input: Input) -> list[Message]:
    if isinstance(input, list):
        if len(input) == 0:
            return []
        if all(isinstance(item, Message) for item in input):
            return input
        elif all(isinstance(item, MessagePart) for item in input):
            return [Message(parts=input)]
        elif all(isinstance(item, str) for item in input):
            return [Message(parts=[MessagePart(content=content) for content in input])]
        else:
            raise TypeError("List with mixed types is not supported")
    else:
        if isinstance(input, str):
            input = MessagePart(content=input)
        if isinstance(input, MessagePart):
            input = Message(parts=[input])
        if isinstance(input, Message):
            input = [input]
        return input
