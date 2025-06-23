# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import RedisStore, RunYield, RunYieldResume, Server
from redis.asyncio import Redis

server = Server()


@server.agent()
async def echo(input: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in input:
        yield message


redis = Redis()
server.run(store=RedisStore(redis=redis))
