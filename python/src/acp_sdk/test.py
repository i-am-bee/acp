import asyncio
from typing import AsyncGenerator
import uuid
from acp_sdk.models import (
    ImageMessagePart,
    Message,
    Await,
    AwaitResume,
    SessionId,
    TextMessagePart,
)
from acp_sdk.server import Agent, serve

from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend.chat import ChatModel, ChatModelParameters
from beeai_framework.backend.message import UserMessage
from beeai_framework.memory import TokenMemory
from beeai_framework.tools.search import DuckDuckGoSearchTool, WikipediaTool
from beeai_framework.tools.weather.openmeteo import OpenMeteoTool

from acp_sdk.server.context import Context


from acp_sdk.client.client import create_client


class EchoAgent(Agent):
    @property
    def name(self):
        return "echo"

    @property
    def description(self):
        return "Echoes everything"

    async def run(self, input: Message, *, context: Context):
        yield input


class LazyEchoAgent(Agent):
    @property
    def name(self):
        return "lazy_echo"

    @property
    def description(self):
        return "Echoes everything with 1 minute delay"

    async def run(self, input: Message, *, context: Context):
        await asyncio.sleep(60)
        yield input


class StreamingEchoAgent(Agent):
    @property
    def name(self):
        return "streaming_echo"

    @property
    def description(self):
        return "Echoes all message parts in a stream"

    async def run(self, input: Message, *, context: Context):
        for part in input:
            yield Message(part)


class AwaitingAgent(Agent):
    async def run(
        self, input: Message, *, context: Context
    ) -> AsyncGenerator[Message | Await, AwaitResume]:
        yield Message(TextMessagePart(content="Hello!"))
        data = yield Await()
        yield Message(TextMessagePart(content=f"Thanks for {data}"))


class BeeAIAgent(Agent):
    def __init__(self):
        self.llm = ChatModel.from_name(
            "ollama:llama3.1",
            ChatModelParameters(temperature=0),
        )

    @property
    def name(self):
        return "beeai"

    @property
    def description(self):
        return "Beeai agent powered by ollama and no tools"

    async def run(self, input: Message, *, context: Context):
        memory = TokenMemory(self.llm)
        await memory.add_many(
            (
                UserMessage(part.content)
                for part in input
                if isinstance(part, TextMessagePart)
            )
        )
        output = await ReActAgent(llm=self.llm, tools=[], memory=memory).run(
            prompt=None
        )
        for content in output.result.get_texts():
            yield Message(TextMessagePart(content=content.text))


class BeeAIAgentAdvanced(Agent):
    def __init__(self):
        self.llm = ChatModel.from_name(
            "ollama:llama3.1",
            ChatModelParameters(temperature=0),
        )
        self.tools = [
            WikipediaTool(),
            OpenMeteoTool(),
            DuckDuckGoSearchTool(),
        ]
        self.memories: dict[SessionId, TokenMemory] = dict()

    @property
    def name(self):
        return "beeai_advanced"

    @property
    def description(self):
        return "Beeai agent powered by ollama with tools and sessions"

    async def session(self, session_id: SessionId | None):
        if session_id and session_id not in self.memories:
            raise ValueError("Memory not found")

        session_id = session_id or str(uuid.uuid4())
        memory = self.memories.get(session_id, TokenMemory(self.llm))
        self.memories[session_id] = memory
        return session_id

    async def run(self, input: Message, *, context: Context):
        await self.memories[context.session_id].add_many(
            (
                UserMessage(part.content)
                for part in input
                if isinstance(part, TextMessagePart)
            )
        )
        output = await ReActAgent(
            llm=self.llm, tools=self.tools, memory=self.memories[context.session_id]
        ).run(prompt=None)
        for content in output.result.get_texts():
            yield Message(TextMessagePart(content=content.text))


def test_server():
    asyncio.run(
        serve(
            EchoAgent(),
            LazyEchoAgent(),
            StreamingEchoAgent(),
            AwaitingAgent(),
            BeeAIAgent(),
            BeeAIAgentAdvanced(),
        )
    )


async def client():
    async with create_client("http://localhost:8000") as client:
        print("## Agents")
        async for x in client.agents():
            print(f"{x.name} | {x.description}")
        print()

        print("## Run sync")
        run = await client.run_sync(
            agent="echo", input=Message(TextMessagePart(content="Howdy!"))
        )
        print(run.output)
        print()

        print("## Run stream")
        async for event in client.run_stream(
            agent="streaming_echo",
            input=Message(
                TextMessagePart(content="Howdy!"),
                TextMessagePart(content=" How are ya?"),
            ),
        ):
            print(event)
        print()

        print("## Run BeeAI")
        run = await client.run_sync(
            agent="beeai",
            input=Message(TextMessagePart(content="Howdy!")),
        )
        print(run.output)
        print()


def test_client():
    asyncio.run(client())
