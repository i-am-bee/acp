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
from code_reviewer_tool import CodeReviewerTool

server = Server()


@server.agent()
async def code_reviewer(input: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(llm=llm, tools=[], memory=TokenMemory(llm))
    response = await agent.run(
        prompt="Please review the following code and provide suggestions for improvement. The code is: " + str(input[0])
    )

    yield MessagePart(content=response.result.text)


@server.agent(name="generator")
async def main_agent(input: list[Message], context: Context) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(
        llm=llm,
        tools=[CodeReviewerTool()],
        templates={
            "system": lambda template: template.update(
                defaults=exclude_none(
                    {
                        "instructions": """
                        You are a professional software engineer. You are given a task implement a code snippet to solve
                        the problem provided by the user. Come up with a code snippet that solves the problem.

                        The code should be in Python.

                        Before sending the code to the user, use the code reviewer tool to review the code.
                        Make sure you adjust the code based on the suggestions provided by the code reviewer tool.

                        Once there are no more suggestions from the code reviewer tool, send the code to the user.
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
