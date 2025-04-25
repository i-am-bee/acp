import asyncio
from functools import reduce

from acp_sdk.client import Client
from acp_sdk.models import MessageAwaitResume, Message, MessagePart


async def handle_resume(client, run_id):
    async for event in client.run_resume_stream(
        run_id=run_id, await_resume=MessageAwaitResume(message=Message(parts=[MessagePart(content="yes")]))
    ):
        print(event)

        if event.type == "run.completed":
            print()
            print(str(event.run.output[-1]))


async def client():
    async with Client(base_url="http://localhost:8000") as client:
        initial_message = Message(parts=[MessagePart(content="Can you generate a password for me?")])

        async for event in client.run_stream(agent="approval_agent", input=[initial_message]):
            print(event)

            if event.type == "run.awaiting":
                await handle_resume(client, event.run.run_id)


if __name__ == "__main__":
    asyncio.run(client())
