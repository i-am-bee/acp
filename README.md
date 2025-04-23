<h1 align="center">
  Agent Communication Protocol (ACP)
</h1>
<h3 align="center">Framework-agnostic agent communication. Unified by design.</h3>

<div align="center">

[![Apache 2.0](https://img.shields.io/badge/Apache%202.0-License-EA7826?style=flat-square&logo=apache&logoColor=white)](https://github.com/i-am-bee/beeai-framework?tab=Apache-2.0-1-ov-file#readme)
[![Follow on Bluesky](https://img.shields.io/badge/Follow%20on%20Bluesky-0285FF?style=flat-square&logo=bluesky&logoColor=white)](https://bsky.app/profile/beeaiagents.bsky.social)
[![Join our Discord](https://img.shields.io/badge/Join%20our%20Discord-7289DA?style=flat-square&logo=discord&logoColor=white)](https://discord.com/invite/NradeA6ZNF)
[![LF AI & Data](https://img.shields.io/badge/LF%20AI%20%26%20Data-0072C6?style=flat-square&logo=linuxfoundation&logoColor=white)](https://lfaidata.foundation/projects/)

</div>

<p align="center">
  <strong><a href="https://agentcommunicationprotocol.dev">Documentation</a></strong> •
  <strong><a href="https://github.com/i-am-bee/acp/blob/main/docs/spec/openapi.yaml">OpenAPI Spec</a></strong> •
  <strong><a href="https://github.com/i-am-bee/acp/blob/main/python">Python SDK</a></strong> •
  <strong><a href="https://github.com/i-am-bee/acp/tree/main/examples">Examples</a></strong>
</p>

<br>

The **Agent Communication Protocol (ACP)** is an **open standard** enabling **seamless communication** between AI agents, regardless of their implementation details. In ACP, an **agent** is a software service that communicates through **multimodal messages**, primarily driven by natural language. The protocol remains **agnostic** to how agents function internally, specifying only the **minimum assumptions** necessary for smooth interoperability. ACP defines a **standardized RESTful API** for managing and executing agents, supporting **synchronous**, **asynchronous**, and **streaming** interactions.

## Core Components

| **Concept**      | **Description** |
|------------------|-----------------|
| **Agent Detail** | **Agent Detail** refers to the metadata that describes an **agent**, including its **name**, **description**, and defined set of **functions** or **behaviors**. It is used in the capability-based model for discovery and communication, allowing other components to understand what an agent can do without accessing its implementation. This metadata enables agents to be found, invoked, and composed into larger systems through their well-defined behaviors. |
| **ACP Server**   | The **ACP Server** is the server-side component that exposes agents through a **REST API**. It consists of an **agent interface**, a **FastAPI app factory**, and a **Uvicorn-based server**. Users can either use the full stack for development or integrate their own **ASGI server** for production environments. |
| **ACP Client**   | The **ACP Client** is a lightweight, **httpx-based client** that supports session management. It provides features like session support via **context managers**, the ability to handle simple requests, maintain persistent sessions, and support **streaming responses**. It is designed to closely mirror the **REST API** for ease of use. |
| **Run**          | A **Run** represents a single execution of an agent with specific **inputs**. It can be executed synchronously using **`run_sync`**, or asynchronously in streams using **`run_stream`**, providing flexibility in how agents are invoked and how results are consumed. A run can also produce **intermediate thoughts** and **final outputs**. |
| **Message**      | A **Message** is the primary data structure for communication between agents and clients. Each message contains one or more **MessageParts** and is associated with a role (e.g., **"user"** or **"assistant"**) to define the perspective of the content. Messages are used to pass information in an agent-to-agent or agent-to-client context. |
| **MessagePart**  | A **MessagePart** is a granular unit of content within a message. Each part has **content** and an optional **role**. It supports various content types, such as **text**, **JSON**, etc. Multiple **MessageParts** are combined to form a complete message that conveys structured information. |
| **Await**        | **Await** is a mechanism that allows agents to pause execution and request additional information from the client before continuing. This creates interactive, **stateful conversations** where agents can ask for clarification or further data as needed. It is implemented using **`MessageAwaitRequest`** and **`MessageAwaitResume`** objects. |

## Quickstart

**1. Create and activate a Python virtual environment**

```sh
python3 -m venv .venv
source .venv/bin/activate
```

**2. Install ACP SDK into the virtual environment**

```sh
pip install acp-sdk
```

**3. Create an agent**

Let’s create a simple "echo agent" that returns any message it receives.

```python
# agent.py
import asyncio
from collections.abc import AsyncGenerator

from acp_sdk.models import Message
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

server = Server()


@server.agent()
async def echo(
    inputs: list[Message], context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in inputs:
        await asyncio.sleep(0.5)
        yield {"thought": "I should echo everything"}
        await asyncio.sleep(0.5)
        yield message


server.run()
```

**4. Start the ACP server**

```sh
python agent.py
```

Your server should now be running at `http://localhost:8000`.

**5. Verify your agent is available**

*Request:*
```sh
curl http://localhost:8000/agents
```

*Response:*
```json
{
  "agents": [
    { "name": "echo", "description": "Echoes everything", "metadata": {} }
  ]
}
```

You should see a JSON response containing your `echo` agent, confirming it's available.

**6. Run the agent via HTTP**

*Request:*
```sh
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
        "agent_name": "echo",
        "inputs": [
          {
            "parts": [
              {
                "content": "Howdy!",
                "content_type": "text/plain"
              }
            ]
          }
        ]
      }'
```

*Response:*
```json
{
  "run_id": "44e480d6-9a3e-4e35-8a03-faa759e19588",
  "agent_name": "echo",
  "session_id": "b30b1946-6010-4974-bd35-89a2bb0ce844",
  "status": "completed",
  "await_request": null,
  "outputs": [
    {
      "parts": [
        {
          "name": null,
          "content_type": "text/plain",
          "content": "Howdy!",
          "content_encoding": "plain",
          "content_url": null
        }
      ]
    }
  ],
  "error": null
}
```

Your response should include the echoed message "Howdy!".

**7. Build an ACP client**

Here’s a simple ACP client to interact with your `echo` agent:

```python
# client.py
import asyncio

from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart


async def example() -> None:
    async with Client(base_url="http://localhost:8000") as client:
        run = await client.run_sync(
            agent="echo",
            inputs=[
                Message(
                    parts=[MessagePart(content="Howdy!", content_type="text/plain")]
                )
            ],
        )
        print(run.outputs)


if __name__ == "__main__":
    asyncio.run(example())
```

**8. Run the ACP client**

```sh
python client.py
```

You should see the echoed response printed to your console. 🎉

## Contributors

We are grateful for the efforts of our initial contributors, who have played a vital role in getting ACP of the ground. As we continue to grow and evolve, we invite others to join our vibrant community and contribute to our project’s ongoing development. For more information, please visit the [Contribute](https://agentcommunicationprotocol.dev/about/contribute) page of our documentation.

![Contributors list](https://contrib.rocks/image?repo=i-am-bee/acp)

## Maintainers

For information about maintainers, see [MAINTAINERS.md](./MAINTAINERS.md).

---

Developed by contributors to the BeeAI project, this initiative is part of the [Linux Foundation AI & Data program](https://lfaidata.foundation/projects/). Its development follows open, collaborative, and community-driven practices.
