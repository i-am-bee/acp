from acp_sdk.models import Message, MessagePart

Input = list[Message] | Message | list[MessagePart] | MessagePart | list[str] | str
