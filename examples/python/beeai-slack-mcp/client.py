import asyncio

from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart


async def run_client() -> None:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(
            agent="slack-agent",
            input=[
                Message(
                    # Pass your instructions below 
                    parts=[MessagePart(content="Post a funny message in C08RV1XUZQA slack channel", content_type="text/plain")]
                )
            ],
        )
        print(run.output)


if __name__ == "__main__":
    asyncio.run(run_client())