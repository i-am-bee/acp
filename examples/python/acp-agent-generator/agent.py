import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from acp_sdk import Message
from acp_sdk.server import Context, Server
from fastapi import FastAPI
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from mcp.shared.memory import create_connected_server_and_client_session
from mcpdoc.main import create_server
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    llm_model_name: str = "openai:gpt-4.1-mini"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")


config = Config()


class AgentGeneratorServer(Server):
    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None]:
        model = init_chat_model(
            model=config.llm_model_name,
            max_tokens=8000,
        )
        async with create_connected_server_and_client_session(
            create_server(
                [
                    {
                        "name": "Agent Communication Protocol Documentation",
                        "llms_txt": "https://agentcommunicationprotocol.dev/llms-full.txt",
                    },
                    {
                        "name": "Langraph Documentation",
                        "llms_txt": "https://langchain-ai.github.io/langgraph/llms.txt",
                    },
                    {
                        "name": "BeeAI Documentation",
                        "llms_txt": "https://docs.beeai.dev/llms-full.txt",
                    },
                    # You can add multiple documentation sources
                    # {
                    #     "name": "Another Documentation",
                    #     "llms_txt": "https://example.com/llms.txt",
                    # },
                ],
                follow_redirects=True,
                timeout=15.0,
                allowed_domains=["*"],
            )
        ) as session:
            self.tools = await load_mcp_tools(session)
            self.graph = create_react_agent(model, self.tools)
            yield


server = AgentGeneratorServer()


@server.agent()
async def acp_agent_generator(input: list[Message], context: Context) -> AsyncGenerator:
    print(input[0].parts[0].content)
    response = await server.graph.ainvoke({"messages": [HumanMessage(input[0].parts[0].content)]})
    print(response)
    yield response["messages"][-1].content


if __name__ == "__main__":
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
