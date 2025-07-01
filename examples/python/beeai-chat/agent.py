from collections.abc import AsyncGenerator

from acp_sdk.models.models import MessagePart, TrajectoryMetadata


import beeai_framework
from acp_sdk import Message
from acp_sdk.models import Metadata, Annotations
from acp_sdk.models.platform import AgentConfiguration, ConfigurationField, PlatformUIAnnotation, PlatformUIType
from acp_sdk.server import Context, Server
from beeai_framework.agents.react import ReActAgent, ReActAgentUpdateEvent
from beeai_framework.backend import AssistantMessage, UserMessage
from beeai_framework.backend.chat import ChatModel, ChatModelParameters
from beeai_framework.memory import TokenMemory
from beeai_framework.tools.search.duckduckgo import DuckDuckGoSearchTool
from beeai_framework.tools.search.wikipedia import WikipediaTool
from beeai_framework.tools.tool import AnyTool
from beeai_framework.tools.weather.openmeteo import OpenMeteoTool

server = Server()

def to_framework_message(role: str, content: str) -> beeai_framework.backend.Message:
    match role:
        case "user":
            return UserMessage(content)
        case role if role == "agent" or (role.startswith("agent/")):
            return AssistantMessage(content)
        case _:
            raise ValueError(f"Unsupported role {role}")


def get_tools(input: list[Message]) -> list[AnyTool]:
    for message in input:
        for part in message.parts:
            if (
                part.metadata
                and part.metadata.kind == "configuration"
                and part.metadata.key == "tools"
                and part.metadata.value is True
            ):
                return [WikipediaTool(), OpenMeteoTool(), DuckDuckGoSearchTool()]

    return []


@server.agent(
    metadata=Metadata(
        annotations=Annotations(
            beeai_ui=PlatformUIAnnotation(
                ui_type=PlatformUIType.CHAT,
                user_greeting="Let's chat!",
                display_name="Chat Agent",
                configuration=[
                    AgentConfiguration(
                        name="tools",
                        description="Enable Tools",
                        type=ConfigurationField.BOOLEAN,
                    )
                ],
            )
        )
    )
)
async def chat_agent(input: list[Message], context: Context) -> AsyncGenerator:
    """
    The agent is an AI-powered conversational system with memory, supporting real-time search, Wikipedia lookups,
    and weather updates through integrated tools.
    """

    # ensure the model is pulled before running
    llm = ChatModel.from_name("ollama:llama3.1", ChatModelParameters(temperature=0))

    # Create agent with memory and tools
    agent = ReActAgent(llm=llm, tools=get_tools(input), memory=TokenMemory(llm))

    history = [message async for message in context.session.load_history()]
    framework_messages = [to_framework_message(message.role, str(message)) for message in history + input]
    await agent.memory.add_many(framework_messages)

    async for data, event in agent.run():
        match (data, event.name):
            case (ReActAgentUpdateEvent(), "update"):
                update = data.update.value
                if not isinstance(update, str):
                    update = update.get_text_content()
                match data.update.key:
                    case "tool_name":
                        yield MessagePart(metadata=TrajectoryMetadata(tool_name=update))
                    case "thought":
                        yield MessagePart(metadata=TrajectoryMetadata(message=update))
                    case "final_answer":
                        yield Message(parts=[MessagePart(content=update)])


if __name__ == "__main__":
    server.run()
