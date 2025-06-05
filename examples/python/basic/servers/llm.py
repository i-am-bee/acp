from collections.abc import AsyncGenerator

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import RunYield, RunYieldResume, Server
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend.chat import ChatModel
from beeai_framework.backend.message import UserMessage
from beeai_framework.memory.token_memory import TokenMemory

server = Server()


@server.agent()
async def llm(inputs: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """LLM agent that processes inputs and returns a response"""

    # Create a llm instance
    llm = ChatModel.from_name("ollama:llama3.1")

    # Create a memory instance
    memory = TokenMemory(llm)

    # Add messages to memory
    for message in inputs:
        await memory.add(UserMessage(str(message)))

    # Create agent with memory and tools
    agent = ReActAgent(llm=llm, tools=[], memory=memory)

    # Run the agent with the memory
    response = await agent.run()

    # Yield the response
    yield MessagePart(content=response.result.text)


server.run()
