import textwrap
from collections.abc import AsyncGenerator

import beeai_framework
from acp_sdk import Message
from acp_sdk.models import MessagePart
from acp_sdk.server import Context, Server
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend import AssistantMessage, Role, UserMessage
from beeai_framework.backend.chat import ChatModel
from beeai_framework.memory import TokenMemory

from run_agent_tool import HandoffTool
from session_storage import SessionStorage

server = Server()
session_storage = SessionStorage()

def to_framework_message(role: Role, content: str) -> beeai_framework.backend.Message:
    match role:
        case Role.USER:
            return UserMessage(content)
        case Role.ASSISTANT:
            return AssistantMessage(content)
        case _:
            raise ValueError(f"Unsupported role {role}")


def to_acp_message(message: beeai_framework.backend.Message) -> Message:
    parts = []
    for content in message.content:
        parts.append(MessagePart(content=content.text, role=message.role))
    return Message(parts=parts)


@server.agent()
async def spanish_agent(input: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")
    print("Calling Spanish agent")

    agent = ReActAgent(
        llm=llm,
        tools=[],
        templates={
            "system": lambda template: template.update(
                defaults={
                    "instructions": "Answer in Spanish",
                    "role": "system",
                }
            )
        },
        memory=TokenMemory(llm),
    )
    await agent.memory.add_many([to_framework_message(Role.USER, str(message)) for message in input])
    response = await agent.run()

    yield to_acp_message(response.result)


@server.agent()
async def english_agent(input: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")
    print("Calling English agent")
    
    agent = ReActAgent(
        llm=llm,
        tools=[],
        templates={
            "system": lambda template: template.update(
                defaults={
                    "instructions": "Answer in English",
                    "role": "system",
                }
            )
        },
        memory=TokenMemory(llm),
    )
    await agent.memory.add_many([to_framework_message(Role.USER, str(message)) for message in input])
    response = await agent.run()

    yield to_acp_message(response.result)


@server.agent(name="assistant")
async def main_agent(input: list[Message], context: Context) -> AsyncGenerator:
    session_storage.append(context.session_id, input)

    llm = ChatModel.from_name("ollama:llama3.1:8b")
    agent = ReActAgent(
        llm=llm,
        tools=[HandoffTool("spanish_agent", context.session_id,session_storage), HandoffTool("english_agent", context.session_id, session_storage)],
        templates={
            "system": lambda template: template.update(
                defaults={
                    "instructions": textwrap.dedent("You've got two agents to handoff to, one is Spanish, the other is English. Based on the language of the request, handoff to the appropriate agent. Once the handoff is done, you should return the result to the user."),
                    "role": "system",
                }
            )
        },
        memory=TokenMemory(llm),
    )
    response = await agent.run(prompt=str(input[0]))
    yield MessagePart(content=response.result.text)

server.run()
