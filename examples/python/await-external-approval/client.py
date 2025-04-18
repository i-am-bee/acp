import asyncio

from acp_sdk.client import Client
from acp_sdk.models import AwaitResume, Message, MessagePart


async def handle_resume(client, run_id):
    async for event in client.run_resume_stream(run_id=run_id, await_resume=AwaitResume()):
        print(event)


async def client():
    async with Client(base_url="http://localhost:8000") as client:
        initial_message = Message(parts=[MessagePart(content="Hi there!")])

        async for event in client.run_stream(agent="approval_agent", inputs=[initial_message]):
            print(event)

            if event.type == "run.awaiting":
                await handle_resume(client, event.run.run_id)


if __name__ == "__main__":
    asyncio.run(client())
