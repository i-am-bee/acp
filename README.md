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
  <strong><a href="https://ibm.biz/agentcommunicationprotocol">Documentation</a></strong> •
  <strong><a href="https://github.com/i-am-bee/beeai-platform/blob/main/docs/acp/spec/openapi.yaml">OpenAPI Spec</a></strong> •
  <strong><a href="https://github.com/i-am-bee/acp/blob/main/python">Python SDK</a></strong> •
  <strong><a href="https://github.com/i-am-bee/acp/tree/main/examples">Examples</a></strong>
</p>

<br>

The **Agent Communication Protocol (ACP)** is an open standard that enables seamless communication between AI agents across different technology stacks and frameworks. It provides a standardized RESTful API for managing and executing agents, supporting **synchronous**, **asynchronous**, and **streamed** interactions for effective agent interoperability.

## Core Components

| **Concept**      | **Description** |
|------------------|-----------------|
| **Agent Detail** | An **agent** is an entity with a **name**, **description**, and a defined set of **functions** or **behaviors**. It operates based on a capability-based model, which is used for **discovery** and **communication**. Agents interact with other agents and systems through well-defined behaviors, enabling effective and predictable operations. |
| **ACP Server**   | The **ACP Server** is the server-side component that exposes agents through a **REST API**. It consists of an **agent interface**, a **FastAPI app factory**, and a **Uvicorn-based server**. Users can either use the full stack for development or integrate their own **ASGI server** for production environments. |
| **ACP Client**   | The **ACP Client** is a lightweight, **httpx-based client** that supports session management. It provides features like session support via **context managers**, the ability to handle simple requests, maintain persistent sessions, and support **streaming responses**. It is designed to closely mirror the **REST API** for ease of use. |
| **Run**          | A **Run** represents a single execution of an agent with specific **inputs**. It can be executed synchronously using **`run_sync`**, or asynchronously in streams using **`run_stream`**, providing flexibility in how agents are invoked and how results are consumed. A run can also produce **intermediate thoughts** and **final outputs**. |
| **Message**      | A **Message** is the primary data structure for communication between agents and clients. Each message contains one or more **MessageParts** and is associated with a role (e.g., **"user"** or **"assistant"**) to define the perspective of the content. Messages are used to pass information in an agent-to-agent or agent-to-client context. |
| **MessagePart**  | A **MessagePart** is a granular unit of content within a message. Each part has **content** and an optional **role**. It supports various content types, such as **text**, **JSON**, etc. Multiple **MessageParts** are combined to form a complete message that conveys structured information. |
| **Await**        | **Await** is a mechanism that allows agents to pause execution and request additional information from the client before continuing. This creates interactive, **stateful conversations** where agents can ask for clarification or further data as needed. It is implemented using **`MessageAwaitRequest`** and **`MessageAwaitResume`** objects. |

## Quickstart

**1. Install Python SDK:** `pip install acp-sdk`

**2. Create agent file**
```python agent.py
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

**3. Set up virtual environment and run agent**
```bash
python3 -m venv env
source venv/bin/activate
python agent.py
```

**4. List available agents to confirm your agent is running**
```bash
curl http://localhost:8000/agents
```

**5. Call your agent**
```bash
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
        "agent_name": "echo",
        "inputs": [
          {
            "parts": [
              {
                "content_type": "text/plain",
                "content": "Howdy!"
              }
            ]
          }
        ]
      }'
```

## Get Involved

Join our [GitHub discussions](https://github.com/orgs/i-am-bee/discussions) to help shape this evolving standard and build the foundation for an open, interoperable agent ecosystem.

## Maintainers

For information about maintainers, see [MAINTAINERS.md](./MAINTAINERS.md).

---

Developed by contributors to the BeeAI project, this initiative is part of the [Linux Foundation AI & Data program](https://lfaidata.foundation/projects/). Its development follows open, collaborative, and community-driven practices.
