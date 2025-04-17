# Agent Communication Protocol SDK for Python

Agent Communication Protocol SDK for Python provides allows developers to serve and consume agents over the Agent Communication Protocol.

## Prerequisites

✅ Python >= 3.11

## Installation

Install to use client:

```shell
pip install acp-sdk[client]
```

Install to use server:

```shell
pip install acp-sdk[server]
```

## Overview

### Core

The core of the SDK exposes [pydantic](https://docs.pydantic.dev/) data models corresponding to REST API requests, responses, resources, events and errors.


### Client

The `client` submodule exposes [httpx](https://www.python-httpx.org/) based client with simple methods for communication over ACP.

```python
async with Client(base_url="http://localhost:8000") as client:
    run = await client.run_sync(agent="echo", inputs=[Message(TextMessagePart(content="Howdy!"))])
    print(run)

```

### Server

The `server` submodule exposes `Agent` class and `agent` decorator together with [fastapi](https://fastapi.tiangolo.com/) application factory, making it easy to expose agents over ACP. Additionaly, it exposes [uvicorn](https://www.uvicorn.org/) based server to serve agents with set up logging, [opentelemetry](https://opentelemetry.io/) and more.

```python
server = Server()

@server.agent()
async def echo(inputs: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in inputs:
        yield {"thought": "I should echo everyting"}
        await asyncio.sleep(0.5)
        yield message


server.run()
```

➡️ Explore more in our [examples library](/python/examples).
