from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import RunYield, RunYieldResume, agent, create_app

# This example demonstrates how to serve agents with you own server


@agent()
async def echo(inputs: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in inputs:
        yield message


app = create_app(echo)

# The app can now be used with any ASGI server

# Run with
#   1. fastapi run examples/servers/standalone.py
#   2. uvicorn examples.servers.standalone:app
#   ...
