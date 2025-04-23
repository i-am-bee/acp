import asyncio
from functools import reduce
import httpx

from acp_sdk.client import Client
from acp_sdk.models import (
    Message,
    MessagePart,
)


async def example() -> None:
    async with Client(client=httpx.AsyncClient(
            base_url="http://localhost:8000",
            timeout=100,
        )) as client, client.session() as session:
        run = await session.run_sync(
            agent="chat_agent", inputs=[Message(parts=[MessagePart(content="Hi, my name is Jon. I like apples. Can you tell me something about them?", content_type="text/plain")])]
        )
        print(str(reduce(lambda x, y: x + y, run.outputs)))
        run = await session.run_sync(
            agent="chat_agent", inputs=[Message(parts=[MessagePart(content="Can you write a poem about my favourite fruit?", content_type="text/plain")])]
        )
        print(str(reduce(lambda x, y: x + y, run.outputs)))


if __name__ == "__main__":
    asyncio.run(example())
