# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncGenerator
from functools import reduce

from acp_sdk import Message
from acp_sdk.models import MessagePart
from acp_sdk.server import Context, Server
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import TokenMemory
from beeai_framework.utils.dicts import exclude_none
from translation_tool import TranslationTool

server = Server()


@server.agent()
async def translation_spanish(input: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(llm=llm, tools=[], memory=TokenMemory(llm))
    response = await agent.run(prompt="Translate the given text to Spanish. The text is: " + str(input))

    yield MessagePart(content=response.result.text)


@server.agent()
async def translation_french(input: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(llm=llm, tools=[], memory=TokenMemory(llm))
    response = await agent.run(prompt="Translate the given text to French. The text is: " + str(input))

    yield MessagePart(content=response.result.text)


@server.agent(name="orchestrator", metadata={"ui": {"type": "handsoff"}})
async def main_agent(input: list[Message], context: Context) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(
        llm=llm,
        tools=[TranslationTool()],
        templates={
            "system": lambda template: template.update(
                defaults=exclude_none(
                    {
                        "instructions": """
                        User can ask for a translation of a text to either Spanish or French or both.
                        Translate the given text to all languages specified in the input. Always use the translation tool
                        to translate the text. Dont't question what is returned by the tool, always return as is to the
                        user even when it does not make sense to you.
                    """,
                        "role": "system",
                    }
                )
            )
        },
        memory=TokenMemory(llm),
    )

    prompt = reduce(lambda x, y: x + y, input)
    response = await agent.run(str(prompt)).observe(
        lambda emitter: emitter.on(
            "update", lambda data, event: print(f"Agent({data.update.key}) 🤖 : ", data.update.parsed_value)
        )
    )

    yield MessagePart(content=response.result.text)


server.run()
