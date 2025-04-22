from collections.abc import AsyncGenerator

import beeai_framework
from acp_sdk import Message
from acp_sdk.client import Client
from acp_sdk.models import MessagePart
from acp_sdk.server import Context, Server
from beeai_framework.backend.chat import ChatModel
from beeai_framework.agents.react import ReActAgent
from beeai_framework.memory import TokenMemory

server = Server()

async def run_agent(agent: str, input: str) -> list[Message]:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(
            agent=agent,
            inputs=[Message(parts=[MessagePart(content=input, content_type="text/plain")])]
        )

    return run.outputs

def get_text_from_messages(messages: list[Message]) -> str:
    if not messages or not messages[0].parts:
        return ""
    return messages[0].parts[0].content

@server.agent(name="translation")
async def translation_agent(inputs: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(llm=llm, tools=[], memory=TokenMemory(llm))
    response = await agent.run(prompt="Translate the given text to Spanish. The text is: " + get_text_from_messages(inputs))

    yield Message(parts=[MessagePart(content=response.result.text)])

@server.agent(name="marketing_copy") 
async def marketing_copy_agent(inputs: list[Message]) -> AsyncGenerator:
    llm = ChatModel.from_name("ollama:llama3.1:8b")

    agent = ReActAgent(llm=llm, tools=[], memory=TokenMemory(llm))
    response = await agent.run(prompt="You are able to generate punchy headlines for a marketing campaign. Provide punchy headline to sell the specified product on users eshop. The product is: " + get_text_from_messages(inputs))

    yield Message(parts=[MessagePart(content=response.result.text)])


@server.agent(name="assistant")
async def main_agent(inputs: list[Message], context: Context) -> AsyncGenerator:
    marketing_copy = await run_agent("marketing_copy", get_text_from_messages(inputs))
    translated_marketing_copy = await run_agent("translation", get_text_from_messages(marketing_copy))

    yield Message(parts=[MessagePart(content=get_text_from_messages(marketing_copy)), MessagePart(content=get_text_from_messages(translated_marketing_copy))])

if __name__ == "__main__":
    server.run()