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


@server.agent(name="router")
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
                        Translate the given text to either Spanish or French using the translation tool.
                        Return only the result from the tool as it is, don't change it.
                    """,
                        "role": "system",
                    }
                )
            )
        },
        memory=TokenMemory(llm),
    )

    prompt = reduce(lambda x, y: x + y, input)
    response = await agent.run(str(prompt))

    yield MessagePart(content=response.result.text)


server.run()
