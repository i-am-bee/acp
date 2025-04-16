import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Self

import httpx
from httpx_sse import EventSource, aconnect_sse
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from pydantic import TypeAdapter

from acp_sdk.models import (
    ACPError,
    Agent,
    AgentName,
    AgentReadResponse,
    AgentsListResponse,
    AwaitResume,
    CreatedEvent,
    Error,
    Message,
    Run,
    RunCancelResponse,
    RunCreateRequest,
    RunCreateResponse,
    RunEvent,
    RunId,
    RunMode,
    RunResumeRequest,
    RunResumeResponse,
    SessionId,
)


class Client:
    def __init__(
        self,
        *,
        base_url: httpx.URL | str = "",
        session_id: SessionId | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.session_id = session_id

        self._client = self._init_client(client)

    def _init_client(self, client: httpx.AsyncClient | None = None) -> httpx.AsyncClient:
        client = client or httpx.AsyncClient(base_url=self.base_url)
        HTTPXClientInstrumentor.instrument_client(client)
        return client

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self._client.__aexit__(exc_type, exc_value, traceback)

    @asynccontextmanager
    async def session(self, session_id: SessionId | None = None) -> AsyncGenerator[Self]:
        yield Client(client=self._client, session_id=session_id or uuid.uuid4())

    async def agents(self) -> AsyncIterator[Agent]:
        response = await self._client.get("/agents")
        self._raise_error(response)
        for agent in AgentsListResponse.model_validate(response.json()).agents:
            yield agent

    async def agent(self, *, name: AgentName) -> Agent:
        response = await self._client.get(f"/agents/{name}")
        self._raise_error(response)
        return AgentReadResponse.model_validate(response.json())

    async def run_sync(self, *, agent: AgentName, input: Message) -> Run:
        response = await self._client.post(
            "/runs",
            content=RunCreateRequest(
                agent_name=agent,
                input=input,
                mode=RunMode.SYNC,
                session_id=self.session_id,
            ).model_dump_json(),
        )
        self._raise_error(response)
        response = RunCreateResponse.model_validate(response.json())
        self._set_session(response)
        return response

    async def run_async(self, *, agent: AgentName, input: Message) -> Run:
        response = await self._client.post(
            "/runs",
            content=RunCreateRequest(
                agent_name=agent,
                input=input,
                mode=RunMode.ASYNC,
                session_id=self.session_id,
            ).model_dump_json(),
        )
        self._raise_error(response)
        response = RunCreateResponse.model_validate(response.json())
        self._set_session(response)
        return response

    async def run_stream(self, *, agent: AgentName, input: Message) -> AsyncIterator[RunEvent]:
        async with aconnect_sse(
            self._client,
            "POST",
            "/runs",
            content=RunCreateRequest(
                agent_name=agent,
                input=input,
                mode=RunMode.STREAM,
                session_id=self.session_id,
            ).model_dump_json(),
        ) as event_source:
            async for event in self._validate_stream(event_source):
                if isinstance(event, CreatedEvent):
                    self._set_session(event.run)
                yield event

    async def run_status(self, *, run_id: RunId) -> Run:
        response = await self._client.get(f"/runs/{run_id}")
        self._raise_error(response)
        return Run.model_validate(response.json())

    async def run_cancel(self, *, run_id: RunId) -> Run:
        response = await self._client.post(f"/runs/{run_id}/cancel")
        self._raise_error(response)
        return RunCancelResponse.model_validate(response.json())

    async def run_resume_sync(self, *, run_id: RunId, await_: AwaitResume) -> Run:
        response = await self._client.post(
            f"/runs/{run_id}",
            json=RunResumeRequest(await_=await_, mode=RunMode.SYNC).model_dump(),
        )
        self._raise_error(response)
        return RunResumeResponse.model_validate(response.json())

    async def run_resume_async(self, *, run_id: RunId, await_: AwaitResume) -> Run:
        response = await self._client.post(
            f"/runs/{run_id}",
            json=RunResumeRequest(await_=await_, mode=RunMode.ASYNC).model_dump(),
        )
        self._raise_error(response)
        return RunResumeResponse.model_validate(response.json())

    async def run_resume_stream(self, *, run_id: RunId, await_: AwaitResume) -> AsyncIterator[RunEvent]:
        async with aconnect_sse(
            self._client,
            "POST",
            f"/runs/{run_id}",
            json=RunResumeRequest(await_=await_, mode=RunMode.STREAM).model_dump(),
        ) as event_source:
            async for event in self._validate_stream(event_source):
                yield event

    async def _validate_stream(
        self,
        event_source: EventSource,
    ) -> AsyncIterator[RunEvent]:
        async for event in event_source.aiter_sse():
            event = TypeAdapter(RunEvent).validate_json(event.data)
            yield event

    def _raise_error(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPError:
            raise ACPError(Error.model_validate(response.json()))

    def _set_session(self, run: Run) -> None:
        self.session_id = run.session_id
