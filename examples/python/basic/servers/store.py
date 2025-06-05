from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import RedisStore, RunYield, RunYieldResume, agent, create_app
from redis.asyncio import Redis

# This example demonstrates how to serve agents with you own server


@agent()
async def echo(input: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in input:
        yield message


redis = Redis()
app = create_app(echo, store=RedisStore(redis=redis))

# The app can now be used with any ASGI server

# Run with
#   1. fastapi run examples/python/basic/servers/store.py
#   ... arbitrary ASGI server ...
