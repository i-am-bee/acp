import asyncio

from acp_sdk.client import Client
from acp_sdk.models import Message, TextMessagePart


async def example() -> None:
    async with Client(base_url="http://localhost:8000") as client:
        async for event in client.run_stream(agent="echo", inputs=[Message(TextMessagePart(content="Howdy!"))]):
            print(event)


if __name__ == "__main__":
    asyncio.run(example())
