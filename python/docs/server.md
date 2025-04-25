# Server

<!-- TOC -->
## Table of Contents
- [Server](#server)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Usage](#usage)
    - [Running a server](#running-a-server)
    - [Standalone application](#standalone-application)
<!-- /TOC -->

---

## Overview

The server module aims to expose arbitrary agents over the Agent Commucation Protocol. Consumers can use this module to avoid protocol-specific technicalities and focus on the agent itself. The modules provides Agent abstractions, FastAPI application factory and Uvicorn-based server.

> [!NOTE]
>
> Location within the sdk: [server](/python/src/acp_sdk/server).

## Usage

The SDK provides `Agent` abstract class and `agent` decorator. Arbitrary agent can be created in by either inheritance from the class or by using the decorator on a generator, coroutine or a regular function.

> [!NOTE]
>
> Location within the sdk: [server.agent](/python/src/acp_sdk/server/agent.py).

### Running a server

The SDK provides `Server` class as a convenience for developers to easily serve agents over ACP. The server allows to easily create and register agents. It sets up logging and optionally telemetry exporters.

<!-- embedme python/examples/servers/echo.py -->

```py
import asyncio
from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

server = Server()


@server.agent()
async def echo(input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in input:
        await asyncio.sleep(0.5)
        yield {"thought": "I should echo everything"}
        await asyncio.sleep(0.5)
        yield message


server.run()
```

> [!NOTE]
>
> Location within the sdk: [server.server](/python/src/acp_sdk/server/server.py).

### Standalone application

The SDK provides `create_app` factory that turns agents into `FastAPI` application. The application implements route handlers, error handlers, unified execution environment and more. The application can be served with arbitrary ASGI compatible server.

<!-- embedme python/examples/servers/standalone.py -->

```py
from collections.abc import AsyncGenerator

from acp_sdk.models import (
    Message,
)
from acp_sdk.server import RunYield, RunYieldResume, agent, create_app

# This example demonstrates how to serve agents with you own server


@agent()
async def echo(input: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in input:
        yield message


app = create_app(echo)

# The app can now be used with any ASGI server

# Run with
#   1. fastapi run examples/servers/standalone.py
#   2. uvicorn examples.servers.standalone:app
#   ...

```

> [!NOTE]
>
> Location within the sdk: [server.app](/python/src/acp_sdk/server/app.py).
