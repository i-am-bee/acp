import asyncio
import base64
import os
import time
from collections.abc import AsyncGenerator, AsyncIterator, Generator
from datetime import timedelta
from threading import Thread

import pytest
import pytest_asyncio
import pytest_postgresql.factories
import pytest_redis.factories
from acp_sdk.models import Artifact, AwaitResume, Error, ErrorCode, Message, MessageAwaitRequest, MessagePart
from acp_sdk.models.errors import ACPError
from acp_sdk.server import Context, Server
from acp_sdk.server.store import MemoryStore, PostgreSQLStore, RedisStore, Store
from psycopg import AsyncConnection
from pytest_postgresql.executor import PostgreSQLExecutor
from pytest_postgresql.executor_noop import NoopExecutor
from pytest_redis.executor import NoopRedis, RedisExecutor
from redis.asyncio import Redis

from e2e.config import Config

REDIS_HOST = os.getenv("REDIS_HOST", None)
REDIS_PORT = os.getenv("REDIS_PORT", None)

POSTGRES_HOST = os.getenv("POSTGRES_HOST", None)
POSTGRES_PORT = os.getenv("POSTGRES_PORT", None)
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", None)

redis_db_proc = (
    pytest_redis.factories.redis_noproc(host=REDIS_HOST, port=int(REDIS_PORT))
    if REDIS_HOST and REDIS_PORT
    else pytest_redis.factories.redis_proc()
)

postgres_db_proc = (
    pytest_postgresql.factories.postgresql_noproc(
        host=POSTGRES_HOST, port=int(POSTGRES_PORT), password=POSTGRES_PASSWORD
    )
    if POSTGRES_HOST and POSTGRES_PORT and POSTGRES_PASSWORD
    else pytest_postgresql.factories.postgresql_proc()
)


@pytest_asyncio.fixture(scope="module", params=["memory", "redis", "postgres"])
async def store(
    request: pytest.FixtureRequest,
    redis_db_proc: RedisExecutor | NoopRedis,
    postgres_db_proc: PostgreSQLExecutor | NoopExecutor,
) -> AsyncGenerator[Store]:
    match request.param:
        case "memory":
            yield MemoryStore(limit=1000, ttl=timedelta(minutes=1))
        case "redis":
            redis = Redis(
                unix_socket_path=redis_db_proc.unixsocket,
            )
            yield RedisStore(redis=redis)
        case "postgres":
            aconn = await AsyncConnection.connect(
                f"user={postgres_db_proc.user} password={postgres_db_proc.password} host={postgres_db_proc.host} port={postgres_db_proc.port}"  # noqa: E501
            )
            async with aconn:
                yield PostgreSQLStore(aconn=aconn)
        case _:
            raise AssertionError()


@pytest.fixture(scope="module")
def server(request: pytest.FixtureRequest, store: Store) -> Generator[None]:
    server = Server()

    @server.agent()
    async def echo(input: list[Message], context: Context) -> AsyncIterator[Message]:
        for message in input:
            yield message

    @server.agent()
    async def slow_echo(input: list[Message], context: Context) -> AsyncIterator[Message]:
        for message in input:
            await asyncio.sleep(1)
            yield message

    @server.agent()
    async def history_echo(input: list[Message], context: Context) -> AsyncIterator[Message]:
        async for message in context.session.load_history():
            yield message
        for message in input:
            yield message

    @server.agent()
    async def awaiter(
        input: list[Message], context: Context
    ) -> AsyncGenerator[Message | MessageAwaitRequest, AwaitResume]:
        yield MessageAwaitRequest(message=Message(parts=[]))
        yield MessagePart(content="empty", content_type="text/plain")

    @server.agent()
    async def failer(input: list[Message], context: Context) -> AsyncIterator[Message]:
        yield Error(code=ErrorCode.INVALID_INPUT, message="Wrong question buddy!")
        raise RuntimeError("Unreachable code")

    @server.agent()
    async def raiser(input: list[Message], context: Context) -> AsyncIterator[Message]:
        raise ACPError(Error(code=ErrorCode.INVALID_INPUT, message="Wrong question buddy!"))

    @server.agent()
    async def sessioner(input: list[Message], context: Context) -> AsyncIterator[Message]:
        assert context.session is not None

        yield MessagePart(content=str(context.session.id), content_type="text/plain")

    @server.agent(
        input_content_types=["text/plain", "application/json"],
        output_content_types=["text/html", "application/json", "application/javascript", "text/css"],
    )
    async def mime_types(input: list[Message], context: Context) -> AsyncIterator[Message]:
        yield MessagePart(content="<h1>HTML Content</h1>", content_type="text/html")
        yield MessagePart(content='{"key": "value"}', content_type="application/json")
        yield MessagePart(content="console.log('Hello');", content_type="application/javascript")
        yield MessagePart(content="body { color: red; }", content_type="text/css")

    @server.agent()
    async def base64_encoding(input: list[Message], context: Context) -> AsyncIterator[Message]:
        yield Message(
            parts=[
                MessagePart(
                    content=base64.b64encode(
                        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
                    ).decode("ascii"),
                    content_type="image/png",
                    content_encoding="base64",
                ),
                MessagePart(content="This is plain text", content_type="text/plain"),
            ]
        )

    @server.agent()
    async def artifact_producer(input: list[Message], context: Context) -> AsyncGenerator[Message | Artifact, None]:
        yield MessagePart(content="Processing with artifacts", content_type="text/plain")
        yield Artifact(name="text-result.txt", content_type="text/plain", content="This is a text artifact result")
        yield Artifact(
            name="data.json", content_type="application/json", content='{"results": [1, 2, 3], "status": "complete"}'
        )
        yield Artifact(
            name="image.png",
            content_type="image/png",
            content=base64.b64encode(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            ).decode("ascii"),
            content_encoding="base64",
        )

    thread = Thread(
        target=server.run, kwargs={"self_registration": False, "store": store, "port": Config.PORT}, daemon=True
    )
    thread.start()

    time.sleep(1)

    yield server

    server.should_exit = True
    thread.join(timeout=2)


@pytest.fixture(scope="module")
def multi_server(request: pytest.FixtureRequest) -> Generator[None]:
    server_one = Server()
    server_two = Server()

    @server_one.agent()
    @server_two.agent()
    async def history_echo(input: list[Message], context: Context) -> AsyncIterator[Message]:
        async for message in context.session.load_history():
            yield message
        for message in input:
            yield message

    thread_one = Thread(
        target=server_one.run, kwargs={"self_registration": False, "port": Config.PORT + 1}, daemon=True
    )
    thread_two = Thread(
        target=server_two.run, kwargs={"self_registration": False, "port": Config.PORT + 2}, daemon=True
    )
    thread_one.start()
    thread_two.start()

    time.sleep(1)

    yield (server_one, server_two)

    server_one.should_exit = True
    server_two.should_exit = True
    thread_one.join(timeout=2)
    thread_two.join(timeout=2)
