# Client

<!-- TOC -->
## Table of Contents
- [Client](#client)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Usage](#usage)
    - [Setting up a client](#setting-up-a-client)
    - [Performing discovery](#performing-discovery)
    - [Running an agent](#running-an-agent)
    - [Using sessions](#using-sessions)
<!-- /TOC -->

---

## Overview

The client module provides a thin ACP client that can be integrated into any application that needs to communicate with ACP agents. It provides the following advantages over raw HTTP client:

- Strong typing
- Error handling
- Stream decoding
- Session management
- Instrumentation

> [!NOTE]
>
> Location within the sdk: [client](/python/src/acp_sdk/client)

## Usage

The client is based on the [httpx.AsyncClient](https://www.python-httpx.org/async/). The usage is very similar as demonstrated below.

### Setting up a client

To set up a simple client, simply provide an URL:

```py
async with Client(base_url="http://localhost:8000") as client:
  ...
```

To use advanced HTTP configuration, provide `httpx` async client:

```py
async with Client(
  client=httpx.AsyncClient(
    base_url="http://localhost:8000",
    headers={"token": "foobar"})
  ) as client:
  ...
```

### Performing discovery

To discover available agents:

```py
async with Client(base_url="http://localhost:8000") as client:
  async for agent in client.agents():
    ...
```

### Running an agent

Agent run can be invoked in three modes:

```py
async with Client(base_url="http://localhost:8000") as client:
  message = Message(parts=[MessagePart(content="Hello")])

  # Async
  run = await client.run_async(agent="agent", input=[message])
  print(run.status)

  # Sync - waits for completion, failure, cancellation or await
  run = await client.run_sync(agent="agent", input=[message])
  print(run.output)
  
  # Stream - as sync but also receives events
  async for event in client.run_stream(agent="agent", input=[message])
    print(event)
```

### Using sessions

Sessions are a mechanism to have multi-turn conversations with agents.

To enter a session, create one from the client:

```py
async with Client(base_url="http://localhost:8000" as client:
    agents = [agent async for agent in client.agents()]

    async with client.session() as session:
        for agent in agents:
            await session.run_sync(agent=agent.name, input=[Message(parts=[MessagePart(content="Hello!")])])
```
