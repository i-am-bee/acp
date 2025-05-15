from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import RunYield, RunYieldResume, agent, create_app
from acp_sdk.server.executor import RunData
from acp_sdk.server.session import Session
from acp_sdk.server.store import RedisStore
from redis.asyncio import Redis

# This example demonstrates how to serve agents with you own server


@agent()
async def echo(input: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in input:
        yield message


redis = Redis()
app = create_app(
    echo, run_store=RedisStore(model=RunData, redis=redis), session_store=RedisStore(model=Session, redis=redis)
)

# The app can now be used with any ASGI server

# Run with
#   1. fastapi run examples/servers/standalone.py
#   2. uvicorn examples.servers.standalone:app
#   ...
