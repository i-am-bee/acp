# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import AsyncGenerator

from acp_sdk import Message
from acp_sdk.models import MessagePart
from acp_sdk.models.models import TrajectoryMetadata
from acp_sdk.server import Context, Server

server = Server()


@server.agent()
async def trajectory_agent(input: list[Message], context: Context) -> AsyncGenerator:
    yield MessagePart(metadata=TrajectoryMetadata(message="Let's test a trajectory log"))
    yield MessagePart(
        metadata=TrajectoryMetadata(
            message="Let's now see how tools work", tool_name="Testing Tool", tool_input={"test": "foobar"}
        )
    )
    yield MessagePart(content="Testing trajectory.")


server.run()
