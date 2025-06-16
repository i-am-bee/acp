import pytest
from acp_sdk.client import Client
from acp_sdk.models import AgentManifest
from acp_sdk.server import Server


@pytest.mark.asyncio
async def test_ping(server: Server, client: Client) -> None:
    await client.ping()
    assert True


@pytest.mark.asyncio
async def test_agents_list(server: Server, client: Client) -> None:
    async for agent in client.agents():
        assert isinstance(agent, AgentManifest)


@pytest.mark.asyncio
async def test_agents_manifest(server: Server, client: Client) -> None:
    agent_name = "echo"
    agent = await client.agent(name=agent_name)
    assert isinstance(agent, AgentManifest)
    assert agent.name == agent_name
