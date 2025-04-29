import pytest
from acp_sdk.client import Client
from acp_sdk.models import Agent
from acp_sdk.server import Server


@pytest.mark.asyncio
async def test_ping(server: Server, client: Client) -> None:
    await client.ping()
    assert True


@pytest.mark.asyncio
async def test_agents_list(server: Server, client: Client) -> None:
    async for agent in client.agents():
        assert isinstance(agent, Agent)


@pytest.mark.asyncio
async def test_agents_details(server: Server, client: Client) -> None:
    agent_name = "echo"
    agent = await client.agent(name=agent_name)
    assert isinstance(agent, Agent)
    assert agent.name == agent_name
