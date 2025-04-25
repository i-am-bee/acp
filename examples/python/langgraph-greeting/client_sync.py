import asyncio

from acp_sdk.client import Client
from acp_sdk.models import (
    Message,
    MessagePart,
)


async def client() -> None:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(
            agent="lang_graph_greeting_agent", input=[Message(parts=[MessagePart(content="Jon")])]
        )
        print(run.output[0].parts[0].content)


if __name__ == "__main__":
    asyncio.run(client())
