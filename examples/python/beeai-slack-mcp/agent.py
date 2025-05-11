from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from beeai_framework.agents import AgentExecutionConfig
from beeai_framework.agents.tool_calling import ToolCallingAgent
from beeai_framework.backend import ChatModel, ChatModelParameters
from beeai_framework.emitter import EventMeta
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools.mcp import MCPTool

from collections.abc import AsyncGenerator

from acp_sdk.models import Message, MessagePart
from acp_sdk.server import RunYield, RunYieldResume, Server, Context

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Load environment variables using pydantic settings
class Settings(BaseSettings):
    bot_token: str = Field(alias='SLACK_BOT_TOKEN')
    team_id: str = Field(alias='SLACK_TEAM_ID')
    path: str = Field(default="", env="PATH")

    model_config = SettingsConfigDict(env_file='.env')  
 
settings = Settings()

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-slack"],
    env={
        "SLACK_BOT_TOKEN": settings.bot_token,
        "SLACK_TEAM_ID": settings.team_id,
        "PATH": settings.path,
    },
)

server = Server()

async def slack_tool(session: ClientSession) -> list[MCPTool]:
    # Discover all Slack tools via MCP client
    slacktools = await MCPTool.from_client(session)
    filter_tool = filter(lambda tool: "slack" in tool.name, slacktools)
    slack = list(filter_tool)
    return slack


async def create_agent(session: ClientSession) -> ToolCallingAgent:
    """Create and configure the agent with tools and LLM"""

    # Other models to try:
    # "llama3.1"
    # "granite3-dense"
    # "deepseek-r1"
    # ensure the model is pulled before running
    llm = ChatModel.from_name(
        "ollama:llama3.1:8b",
        ChatModelParameters(temperature=0),
    )

    # Configure tools
    slack = await slack_tool(session)

    # Create agent with memory and tools and custom system prompt template
    agent = ToolCallingAgent(
        llm=llm,
        tools=slack ,
        memory=UnconstrainedMemory(),
        templates={
            "system": lambda template: template.update(
                defaults={
                    "instructions": """IMPORTANT: When the user mentions Slack, you must interact with the Slack tool before sending the final answer.""",
                }
            )
        },
    )
    return agent


def print_events(data: Any, event: EventMeta) -> None:
    """Print agent events"""
    if event.name in ["start", "retry", "update", "success", "error"]:
        print(f"\n** Event ({event.name}): {event.path} **\n{data}")


@server.agent("slack-agent")
async def slack_agent(input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Agent which uses MCP tools to interact with Slack"""
    async with stdio_client(server_params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        # Create agent
        agent = await create_agent(session)

        # Run agent with the prompt
        response = await agent.run(
            prompt=str(input[0]),
            execution=AgentExecutionConfig(max_retries_per_step=3, total_max_retries=10, max_iterations=20),
        ).on("*", print_events)
        
        yield MessagePart(content=response.result.text)
        
if __name__ == "__main__":
    try:
        # Run the ACP server
        server.run()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")