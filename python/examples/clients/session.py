import asyncio

from acp_sdk.client import Client
from acp_sdk.models import (
    Message,
    TextMessagePart,
)


async def example() -> None:
    async with Client(base_url="http://localhost:8000") as client, client.session() as session:
        run = await session.run_sync(agent="historian", inputs=[Message(TextMessagePart(content="Howdy!"))])
        run = await session.run_sync(agent="historian", inputs=[Message(TextMessagePart(content="Howdy again!"))])
        print(run.outputs)


if __name__ == "__main__":
    asyncio.run(example())
