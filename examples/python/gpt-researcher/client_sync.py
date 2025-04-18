import asyncio

from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart


async def client() -> None:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(
            agent="gpt_researcher",
            inputs=[
                Message(
                    parts=[
                        MessagePart(
                            content="Protocols focused on agent to agent communication",
                            content_type="text/plain",
                        )
                    ]
                )
            ],
        )
        print(run)


if __name__ == "__main__":
    asyncio.run(client())
