# Agent Communication Protocol SDK for Python

Agent Communication Protocol SDK for Python helps developers to serve and consume agents over the Agent Communication Protocol.

## Prerequisites

✅ Python >= 3.11

## Installation

Install according to your Python package manager:

- `uv add acp-sdk`
- `pip install acp-sdk`
- `poetry add acp-sdk`
- ...

## Quickstart

Register an agent and run the server:

```py
server = Server()

@server.agent()
async def echo(input: list[Message]):
    """Echoes everything"""
    for message in input:
        yield message

server.run(port=8000)
```

From another process, connect to the server and run the agent:

```py
async with Client(base_url="http://localhost:8000") as client:
    run = await client.run_sync(agent="echo", input=[Message(parts=[MessagePart(content="Howdy!")])])
    print(run)

```


➡️ Explore more in our [examples library](/examples/python).
