# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio
import base64
from collections.abc import AsyncIterator

from acp_sdk.models import Artifact, Error, ErrorCode, Message, MessageAwaitRequest, MessagePart
from acp_sdk.models.errors import ACPError
from acp_sdk.server import Context, Server

PORT = 8000


def create_server() -> Server:
    server = Server()

    @server.agent()
    async def echo(input: list[Message], context: Context):
        for message in input:
            yield message

    @server.agent()
    async def history_echo(input: list[Message], context: Context) -> AsyncIterator[Message]:
        async for message in context.session.load_history():
            yield message
        for message in input:
            yield message

    @server.agent()
    async def slow_echo(input: list[Message], context: Context):
        for message in input:
            await asyncio.sleep(1)
            yield message

    @server.agent()
    async def awaiter(input: list[Message], context: Context):
        yield MessageAwaitRequest(message=Message(parts=[]))
        yield MessagePart(content="empty", content_type="text/plain")

    @server.agent()
    async def failer(input: list[Message], context: Context):
        yield Error(code=ErrorCode.INVALID_INPUT, message="Wrong question buddy!")
        raise RuntimeError("Unreachable code")

    @server.agent()
    async def raiser(input: list[Message], context: Context):
        raise ACPError(Error(code=ErrorCode.INVALID_INPUT, message="Wrong question buddy!"))

    @server.agent()
    async def sessioner(input: list[Message], context: Context):
        assert context.session_id is not None
        yield MessagePart(content=str(context.session_id), content_type="text/plain")

    @server.agent()
    async def mime_types(input: list[Message], context: Context):
        yield MessagePart(content="<h1>HTML Content</h1>", content_type="text/html")
        yield MessagePart(content='{"key": "value"}', content_type="application/json")
        yield MessagePart(content="console.log('Hello');", content_type="application/javascript")
        yield MessagePart(content="body { color: red; }", content_type="text/css")

    @server.agent()
    async def base64_encoding(input: list[Message], context: Context):
        yield Message(
            parts=[
                MessagePart(
                    content=base64.b64encode(
                        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
                        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
                    ).decode("ascii"),
                    content_type="image/png",
                    content_encoding="base64",
                ),
                MessagePart(content="This is plain text", content_type="text/plain"),
            ]
        )

    @server.agent()
    async def artifact_producer(input: list[Message], context: Context):
        yield MessagePart(content="Processing with artifacts", content_type="text/plain")
        yield Artifact(name="text-result.txt", content_type="text/plain", content="This is a text artifact result")
        yield Artifact(
            name="data.json", content_type="application/json", content='{"results": [1, 2, 3], "status": "complete"}'
        )
        yield Artifact(
            name="image.png",
            content_type="image/png",
            content=base64.b64encode(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
                b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            ).decode("ascii"),
            content_encoding="base64",
        )

    return server


def main():
    server = create_server()

    try:
        print(f"Server is running on port {PORT} — press Ctrl+C to stop.")
        server.run(port=PORT)
    except KeyboardInterrupt:
        print("\nShutting down server...")


if __name__ == "__main__":
    main()
