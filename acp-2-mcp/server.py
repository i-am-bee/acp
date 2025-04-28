import asyncio
from functools import reduce

from acp_sdk.client import Client
from acp_sdk.models import Agent, RunStatus
from mcp.server.fastmcp import FastMCP


async def serve(acp_url: str) -> None:
    server = FastMCP("acp2mcp")

    async with Client(base_url=acp_url) as client:

        @server.tool(name="run_agent", description="Runs an agent with given input")
        async def run_agent(agent: str, input: str) -> str:
            run = await client.run_sync(input, agent=agent)
            match run.status:
                case RunStatus.COMPLETED:
                    return str(reduce(lambda x, y: x + y, run.output))
                case RunStatus.FAILED:
                    raise RuntimeError("Agent failed with error:", run.error)
                case _:
                    raise RuntimeError(f"Agent {run.status.value}")

        def register_agent(agent: Agent) -> None:
            @server.resource(
                uri=f"acp://agents/{agent.name}",
                name=agent.name,
                description=agent.description,
                mime_type="application/json",
            )
            async def read_agent() -> str:
                return agent.model_dump_json()

        async for agent in client.agents():
            register_agent(agent)

        await server.run_stdio_async()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="mcp2acp", description="Serve ACP agents over MCP")
    parser.add_argument("url", type=str, help="The URL of an ACP server")

    args = parser.parse_args()

    asyncio.run(serve(acp_url=args.url))
