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

## Core Concepts

- Agent Detail
- ACP Server
- ACP Client
- Run
- Message
- MessagePart
- Await

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
