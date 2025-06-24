import asyncio

import pytest
from acp_sdk.client import Client
from acp_sdk.models import (
    Message,
    MessagePart,
)
from acp_sdk.models.models import Session
from acp_sdk.server import Server

agent = "history_echo"
input = [Message(parts=[MessagePart(content="Hello!")])]
output = [message.model_copy(update={"role": f"agent/{agent}"}) for message in input]


@pytest.mark.asyncio
async def test_session(server: Server, client: Client) -> None:
    async with client.session() as session:
        run = await session.run_sync(agent=agent, input=input)
        assert run.output == output
        run = await session.run_sync(agent=agent, input=input)
        assert run.output == output * 3


@pytest.mark.asyncio
async def test_session_refresh(server: Server, client: Client) -> None:
    async with client.session() as session:
        await session.run_async(agent=agent, input=input)
        await asyncio.sleep(2)
        sess = await session.refresh_session()
        assert len(sess.history) == len(input) * 2


@pytest.mark.asyncio
async def test_session_multi_client(server: Server, client: Client) -> None:
    session = Session()

    async with client.session(session) as session_client:
        run = await session_client.run_sync(input, agent=agent)
        assert run.output == output
        print(run.session_id)

    async with client.session(session) as session_client:
        run = await session_client.run_sync(input, agent=agent)
        assert run.output == output * 3


@pytest.mark.asyncio
async def test_distributed_session(multi_server: tuple[Server, Server]) -> None:
    one, two = multi_server
    one_url = f"http://localhost:{one.server.config.port}"
    two_url = f"http://localhost:{two.server.config.port}"
    async with Client() as client, client.session() as session:
        run = await session.run_sync(input, agent=agent, base_url=one_url)
        assert run.output == output
        run = await session.run_sync(input, agent=agent, base_url=two_url)
        assert run.output == output * 3
        run = await session.run_sync(input, agent=agent, base_url=one_url)
        assert run.output == output * 7
