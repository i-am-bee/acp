# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncGenerator

from acp_sdk import Message
from acp_sdk.client.client import Client
from acp_sdk.models import MessagePart
from acp_sdk.server import Context, Server
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import TokenMemory

import asyncio

server = Server()


async def run_agent(agent: str, input: str) -> list[Message]:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(
            agent=agent, input=input
        )

    return run.output


@server.agent()
async def translation_spanish(input: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(llm=llm, tools=[], memory=TokenMemory(llm))
    response = await agent.run(
        prompt="Translate the given English text to Spanish. Return only the translated text. The text is: "
        + str(input)
    )

    yield MessagePart(content=response.result.text)


@server.agent()
async def translation_french(input: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(llm=llm, tools=[], memory=TokenMemory(llm))
    response = await agent.run(
        prompt="Translate the given English text to French. Return only the translated text. The text is: " + str(input)
    )

    yield MessagePart(content=response.result.text)


@server.agent()
async def aggregator(input: list[Message], context: Context) -> AsyncGenerator:
    spanish_result, english_result = await asyncio.gather(
        run_agent("translation_spanish", str(input[0])), run_agent("translation_french", str(input[0]))
    )

    yield MessagePart(content=str(spanish_result[0]), language="Spanish")
    yield MessagePart(content=str(english_result[0]), language="French")


server.run()
