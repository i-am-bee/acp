import asyncio
import sys

from acp_sdk import GenericEvent, Message, MessageCompletedEvent, MessagePartEvent
from acp_sdk.client import Client
from acp_sdk.models import MessagePart


async def run_client() -> None:
    async with Client(base_url="http://localhost:8000") as client:
        user_message_input = Message(parts=[MessagePart(content=input("URL: "))])
        async for event in client.run_stream(agent="song_writer_agent", input=[user_message_input]):
            match event:
                case MessagePartEvent(part=MessagePart(content=content)):
                    print(content)
                case GenericEvent():
                    print("\nℹ️ Agent Event:")
                    for key, value in event.generic.model_dump().items():
                        value = value.replace("\n", " ")
                        value = f"{value[:100]}..." if len(value) > 100 else value
                        print(f"{key}: {value}")
                case MessageCompletedEvent():
                    print()
                case _:
                    print(f"ℹ️ {event.type}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(run_client())
