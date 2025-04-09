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

### Client

The `client` submodule exposes [httpx]() based client with simple methods for communication over ACP.

```python
async with Client(base_url="http://localhost:8000") as client:
    run = await client.run_sync(agent="echo", input=Message(TextMessagePart(content="Howdy!")))
    print(run.output)
```

### Server

The `server` submodule exposes [fastapi] application factory that makes it easy to expose any agent over ACP.

```python
class EchoAgent(Agent):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes everything"

    async def run(self, input: Message, *, context: Context) -> AsyncGenerator[Message | Await, AwaitResume]:
        for part in input:
            await asyncio.sleep(0.5)
            yield {"thought": "I should echo everyting"}
            yield Message(part)


serve(EchoAgent())
```

➡️ Explore more in our [examples library](/python/examples).
