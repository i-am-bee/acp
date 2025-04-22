from collections.abc import AsyncGenerator

import beeai_framework
from acp_sdk import Message
from acp_sdk.models import MessagePart
from acp_sdk.server import Context, Server
from beeai_framework.agents.react import ReActAgent, ReActAgentUpdateEvent
from beeai_framework.backend import AssistantMessage, Role, UserMessage
from beeai_framework.backend.chat import ChatModel, ChatModelParameters
from beeai_framework.memory import TokenMemory
from beeai_framework.tools.search.duckduckgo import DuckDuckGoSearchTool
from beeai_framework.tools.search.wikipedia import WikipediaTool
from beeai_framework.tools.tool import AnyTool
from beeai_framework.tools.weather.openmeteo import OpenMeteoTool

server = Server()


def to_framework_message(role: Role, content: str) -> beeai_framework.backend.Message:
    match role:
        case Role.USER:
            return UserMessage(content)
        case Role.ASSISTANT:
            return AssistantMessage(content)
        case _:
            raise ValueError(f"Unsupported role {role}")


@server.agent()
async def chat_agent(inputs: list[Message], context: Context) -> AsyncGenerator:
    """Request approval and respond to user's confirmation."""

    # ensure the model is pulled before running
    llm = ChatModel.from_name("ollama:llama3.1", ChatModelParameters(temperature=0))

    # Configure tools
    tools: list[AnyTool] = [WikipediaTool(), OpenMeteoTool(), DuckDuckGoSearchTool()]

    # Create agent with memory and tools
    agent = ReActAgent(llm=llm, tools=tools, memory=TokenMemory(llm))

    framework_messages = [to_framework_message(Role(message.parts[0].role), str(message)) for message in inputs]
    await agent.memory.add_many(framework_messages)

    update_idx = 0
    async for data, _event in agent.run():
        match data:
            case ReActAgentUpdateEvent():
                update_idx += 1
                if update_idx > 1 and data.update.value == data.update.parsed_value:
                    update_idx = 0
                    continue
                update = data.update.value
                if not isinstance(update, str):
                    update = update.get_text_content()
                match data.update.key:
                    case "thought" | "tool_name" | "tool_input" | "tool_output":
                        yield {data.update.key: update}
                    case "final_answer":
                        yield MessagePart(content=update, role="assistant")
                last_key = data.update.key


if __name__ == "__main__":
    server.run()
