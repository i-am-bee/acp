import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Self

import httpx
from httpx_sse import EventSource, aconnect_sse
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from pydantic import TypeAdapter

from acp_sdk.instrumentation import get_tracer
from acp_sdk.models import (
    ACPError,
    Agent,
    AgentName,
    AgentReadResponse,
    AgentsListResponse,
    AwaitResume,
    Error,
    Event,
    Message,
    Run,
    RunCancelResponse,
    RunCreatedEvent,
    RunCreateRequest,
    RunCreateResponse,
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
        timeout: httpx.Timeout | None = None,
        session_id: SessionId | None = None,
        client: httpx.AsyncClient | None = None,
        instrument: bool = True,
    ) -> None:
        self._session_id = session_id
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout)
        if instrument:
            HTTPXClientInstrumentor.instrument_client(self._client)

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client

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
        session_id = session_id or uuid.uuid4()
        with get_tracer().start_as_current_span("session", attributes={"acp.session": str(session_id)}):
            yield Client(client=self._client, session_id=session_id, instrument=False)

    async def agents(self) -> AsyncIterator[Agent]:
        response = await self._client.get("/agents")
        self._raise_error(response)
        for agent in AgentsListResponse.model_validate(response.json()).agents:
            yield agent

    async def agent(self, *, name: AgentName) -> Agent:
        response = await self._client.get(f"/agents/{name}")
        self._raise_error(response)
        return AgentReadResponse.model_validate(response.json())

    async def run_sync(self, *, agent: AgentName, inputs: list[Message]) -> Run:
        response = await self._client.post(
            "/runs",
            content=RunCreateRequest(
                agent_name=agent,
                inputs=inputs,
                mode=RunMode.SYNC,
                session_id=self._session_id,
            ).model_dump_json(),
        )
        self._raise_error(response)
        response = RunCreateResponse.model_validate(response.json())
        self._set_session(response)
        return response

    async def run_async(self, *, agent: AgentName, inputs: list[Message]) -> Run:
        response = await self._client.post(
            "/runs",
            content=RunCreateRequest(
                agent_name=agent,
                inputs=inputs,
                mode=RunMode.ASYNC,
                session_id=self._session_id,
            ).model_dump_json(),
        )
        self._raise_error(response)
        response = RunCreateResponse.model_validate(response.json())
        self._set_session(response)
        return response

    async def run_stream(self, *, agent: AgentName, inputs: list[Message]) -> AsyncIterator[Event]:
        async with aconnect_sse(
            self._client,
            "POST",
            "/runs",
            content=RunCreateRequest(
                agent_name=agent,
                inputs=inputs,
                mode=RunMode.STREAM,
                session_id=self._session_id,
            ).model_dump_json(),
        ) as event_source:
            async for event in self._validate_stream(event_source):
                if isinstance(event, RunCreatedEvent):
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

    async def run_resume_sync(self, *, run_id: RunId, await_resume: AwaitResume) -> Run:
        response = await self._client.post(
            f"/runs/{run_id}",
            content=RunResumeRequest(await_resume=await_resume, mode=RunMode.SYNC).model_dump_json(),
        )
        self._raise_error(response)
        return RunResumeResponse.model_validate(response.json())

    async def run_resume_async(self, *, run_id: RunId, await_resume: AwaitResume) -> Run:
        response = await self._client.post(
            f"/runs/{run_id}",
            content=RunResumeRequest(await_resume=await_resume, mode=RunMode.ASYNC).model_dump_json(),
        )
        self._raise_error(response)
        return RunResumeResponse.model_validate(response.json())

    async def run_resume_stream(self, *, run_id: RunId, await_resume: AwaitResume) -> AsyncIterator[Event]:
        async with aconnect_sse(
            self._client,
            "POST",
            f"/runs/{run_id}",
            content=RunResumeRequest(await_resume=await_resume, mode=RunMode.STREAM).model_dump_json(),
        ) as event_source:
            async for event in self._validate_stream(event_source):
                yield event

    async def _validate_stream(
        self,
        event_source: EventSource,
    ) -> AsyncIterator[Event]:
        if event_source.response.is_error:
            await event_source.response.aread()
            self._raise_error(event_source.response)
        async for event in event_source.aiter_sse():
            event = TypeAdapter(Event).validate_json(event.data)
            yield event

    def _raise_error(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPError:
            raise ACPError(Error.model_validate(response.json()))

    def _set_session(self, run: Run) -> None:
        self._session_id = run.session_id
