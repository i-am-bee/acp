# Create server parameters for stdio connection
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from acp_sdk.server import Context, Server
from collections.abc import AsyncGenerator
from acp_sdk import Message
from langchain_core.messages import HumanMessage
import asyncio
from contextlib import AsyncExitStack
import os

# Load environment variables from .env file
load_dotenv()



class SessionManager:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.tools = None
        self.agent = None
        self.initialized = False
        
        # Create LLM model
        self.model = init_chat_model(
            model=os.getenv("LLM_MODEL_NAME", "openai:gpt-4.1-mini"),
            max_tokens= 8000,
        )
        
        self.server_params = StdioServerParameters(
            command="python",
            args=['mcpdoctool.py'],
            transport="stdio",
        )
    
    async def initialize(self):
        if self.initialized:
            return
        
        try:
            # Setup stdio client with exit stack to manage resources
            stdio_context = await self.exit_stack.enter_async_context(stdio_client(self.server_params))
            read_stream, write_stream = stdio_context
            
            # Setup session
            session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
            
            # Initialize the connection
            await session.initialize()
            
            # Get tools
            self.tools = await load_mcp_tools(session)
            
            # Create the agent
            self.agent = create_react_agent(self.model, self.tools)
            
            self.initialized = True
            print("Session initialized with tools and agent ready")
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

@server.agent()
async def acp_agent_generator(input: list[Message], context: Context) -> AsyncGenerator:
    # Ensure session is initialized
    if not session_manager.initialized:
        print("Session not initialized, initializing now...")
        await session_manager.initialize()
    
    print(input[0].parts[0].content)
    response = await session_manager.agent.ainvoke({'messages': [HumanMessage(input[0].parts[0].content)]})
    print(response)
    yield response['messages'][-1].content



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