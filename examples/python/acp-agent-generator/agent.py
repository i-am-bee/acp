# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

# Create server parameters for stdio connection
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from pydantic_settings import BaseSettings
from acp_sdk.server import Context, Server
from collections.abc import AsyncGenerator
from acp_sdk import Message
from langchain_core.messages import HumanMessage
import asyncio
from contextlib import AsyncExitStack



class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    LLM_MODEL_NAME: str
    OPENAI_API_KEY: str = None
    ANTHROPIC_API_KEY: str = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class SessionManager:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.tools = None
        self.agent = None
        self.initialized = False
        self.server_params = StdioServerParameters(
            command="python",
            args=["mcpdoctool.py"],
            transport="stdio",
        )

    
    async def initialize(self):
        if self.initialized:
            return

        try:
            # Setup stdio client with exit stack to manage resources
            stdio_context = await self.exit_stack.enter_async_context(
                stdio_client(self.server_params)
            )
            read_stream, write_stream = stdio_context

            # Setup session
            session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Initialize the connection
            await session.initialize()

            # Get tools
            self.tools = await load_mcp_tools(session)
            
            self.initialized = True
            print("Session initialized with tools")
        except Exception as e:
            print(f"Error initializing session: {e}")
            # Clean up any resources that were set up
            await self.exit_stack.aclose()
            raise

    async def cleanup(self):
        await self.exit_stack.aclose()


# Create server and session manager
server = Server()
session_manager = SessionManager()

# Load settings from environment variables
settings = Settings()

if settings.OPENAI_API_KEY and settings.LLM_MODEL_NAME.startswith("openai") :
    api_key = settings.OPENAI_API_KEY
elif settings.ANTHROPIC_API_KEY and settings.LLM_MODEL_NAME.startswith("anthropic"):
    api_key = settings.ANTHROPIC_API_KEY
else:
    raise ValueError("No API key provided. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in the .env file.")


@server.agent()
async def acp_agent_generator(input: list[Message], context: Context) -> AsyncGenerator:
    # Ensure session is initialized
    if not session_manager.initialized:
        print("Session not initialized, initializing now...")
        await session_manager.initialize()

    # Create LLM model
    model = init_chat_model(
        model=settings.LLM_MODEL_NAME,
        max_tokens=8000,
        temperature=0,
        api_key=api_key,
    ).bind_tools(session_manager.tools, parallel_tool_calls=False)
    
    # Create the agent
    system_prompt = """Use the documentation sources provided to answer the user's question. 
    DO NOT ask the user for clarification."""
    agent = create_react_agent(model, session_manager.tools, prompt=system_prompt)

    response = await agent.ainvoke(
        {"messages": [HumanMessage(input[0].parts[0].content)]},
    )
    yield response["messages"][-1].content


if __name__ == "__main__":
    try:
        # Run everything in a single event loop
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        # Create a new event loop for cleanup since we're outside async context
        loop = asyncio.new_event_loop()
        loop.run_until_complete(session_manager.cleanup())
        loop.close()
