import ssl
import typing
import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Self

import httpx
from httpx_sse import EventSource, aconnect_sse
from pydantic import TypeAdapter

from acp_sdk.client.types import Input
from acp_sdk.client.utils import input_to_messages
from acp_sdk.instrumentation import get_tracer
from acp_sdk.models import (
    ACPError,
    Agent,
    AgentName,
    AgentReadResponse,
    AgentsListResponse,
    AwaitResume,
    Error,
    ErrorEvent,
    Event,
    PingResponse,
    Run,
    RunCancelResponse,
    RunCreateRequest,
    RunCreateResponse,
    RunEventsListResponse,
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
        session_id: SessionId | None = None,
        client: httpx.AsyncClient | None = None,
        auth: httpx._types.AuthTypes | None = None,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        timeout: httpx._types.TimeoutTypes = None,
        verify: ssl.SSLContext | str | bool = True,
        cert: httpx._types.CertTypes | None = None,
        http1: bool = True,
        http2: bool = False,
        proxy: httpx._types.ProxyTypes | None = None,
        mounts: None | (typing.Mapping[str, httpx.AsyncBaseTransport | None]) = None,
        follow_redirects: bool = False,
        limits: httpx.Limits = httpx._config.DEFAULT_LIMITS,
        max_redirects: int = httpx._config.DEFAULT_MAX_REDIRECTS,
        event_hooks: None | (typing.Mapping[str, list[httpx._client.EventHook]]) = None,
        base_url: httpx.URL | str = "",
        transport: httpx.AsyncBaseTransport | None = None,
        trust_env: bool = True,
    ) -> None:
        self._session_id = session_id
        self._client = client or httpx.AsyncClient(
            auth=auth,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            verify=verify,
            cert=cert,
            http1=http1,
            http2=http2,
            proxy=proxy,
            mounts=mounts,
            follow_redirects=follow_redirects,
            limits=limits,
            max_redirects=max_redirects,
            event_hooks=event_hooks,
            base_url=base_url,
            transport=transport,
            trust_env=trust_env,
        )

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
            yield Client(client=self._client, session_id=session_id)

    async def agents(self, *, base_url: httpx.URL | str | None = None) -> AsyncIterator[Agent]:
        response = await self._client.get(self._create_url("/agents", base_url=base_url))
        self._raise_error(response)
        for agent in AgentsListResponse.model_validate(response.json()).agents:
            yield agent

    async def agent(self, *, name: AgentName, base_url: httpx.URL | str | None = None) -> Agent:
        response = await self._client.get(self._create_url(f"/agents/{name}", base_url=base_url))
        self._raise_error(response)
        response = AgentReadResponse.model_validate(response.json())
        return Agent(**response.model_dump())

    async def ping(self, *, base_url: httpx.URL | str | None = None) -> bool:
        response = await self._client.get(self._create_url("/ping", base_url=base_url))
        self._raise_error(response)
        PingResponse.model_validate(response.json())
        return

    async def run_sync(self, input: Input, *, agent: AgentName, base_url: httpx.URL | str | None = None) -> Run:
        response = await self._client.post(
            self._create_url("/runs", base_url=base_url),
            content=RunCreateRequest(
                agent_name=agent,
                input=input_to_messages(input),
                mode=RunMode.SYNC,
                session_id=self._session_id,
            ).model_dump_json(),
        )
        self._raise_error(response)
        response = RunCreateResponse.model_validate(response.json())
        return Run(**response.model_dump())

    async def run_async(self, input: Input, *, agent: AgentName, base_url: httpx.URL | str | None = None) -> Run:
        response = await self._client.post(
            self._create_url("/runs", base_url=base_url),
            content=RunCreateRequest(
                agent_name=agent,
                input=input_to_messages(input),
                mode=RunMode.ASYNC,
                session_id=self._session_id,
            ).model_dump_json(),
        )
        self._raise_error(response)
        response = RunCreateResponse.model_validate(response.json())
        return Run(**response.model_dump())

    async def run_stream(
        self, input: Input, *, agent: AgentName, base_url: httpx.URL | str | None = None
    ) -> AsyncIterator[Event]:
        async with aconnect_sse(
            self._client,
            "POST",
            self._create_url("/runs", base_url=base_url),
            content=RunCreateRequest(
                agent_name=agent,
                input=input_to_messages(input),
                mode=RunMode.STREAM,
                session_id=self._session_id,
            ).model_dump_json(),
        ) as event_source:
            async for event in self._validate_stream(event_source):
                yield event

    async def run_status(self, *, run_id: RunId, base_url: httpx.URL | str | None = None) -> Run:
        response = await self._client.get(self._create_url(f"/runs/{run_id}", base_url=base_url))
        self._raise_error(response)
        return Run.model_validate(response.json())

    async def run_events(self, *, run_id: RunId, base_url: httpx.URL | str | None = None) -> AsyncIterator[Event]:
        response = await self._client.get(self._create_url(f"/runs/{run_id}/events", base_url=base_url))
        self._raise_error(response)
        response = RunEventsListResponse.model_validate(response.json())
        for event in response.events:
            yield event

    async def run_cancel(self, *, run_id: RunId, base_url: httpx.URL | str | None = None) -> Run:
        response = await self._client.post(self._create_url(f"/runs/{run_id}/cancel", base_url=base_url))
        self._raise_error(response)
        response = RunCancelResponse.model_validate(response.json())
        return Run(**response.model_dump())

    async def run_resume_sync(
        self, await_resume: AwaitResume, *, run_id: RunId, base_url: httpx.URL | str | None = None
    ) -> Run:
        response = await self._client.post(
            self._create_url(f"/runs/{run_id}", base_url=base_url),
            content=RunResumeRequest(await_resume=await_resume, mode=RunMode.SYNC).model_dump_json(),
        )
        self._raise_error(response)
        response = RunResumeResponse.model_validate(response.json())
        return Run(**response.model_dump())

    async def run_resume_async(
        self, await_resume: AwaitResume, *, run_id: RunId, base_url: httpx.URL | str | None = None
    ) -> Run:
        response = await self._client.post(
            self._create_url(f"/runs/{run_id}", base_url=base_url),
            content=RunResumeRequest(await_resume=await_resume, mode=RunMode.ASYNC).model_dump_json(),
        )
        self._raise_error(response)
        response = RunResumeResponse.model_validate(response.json())
        return Run(**response.model_dump())

    async def run_resume_stream(
        self, await_resume: AwaitResume, *, run_id: RunId, base_url: httpx.URL | str | None = None
    ) -> AsyncIterator[Event]:
        async with aconnect_sse(
            self._client,
            "POST",
            self._create_url(f"/runs/{run_id}", base_url=base_url),
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
            event: Event = TypeAdapter(Event).validate_json(event.data)
            if isinstance(event, ErrorEvent):
                raise ACPError(error=event.error)
            yield event

    def _raise_error(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPError:
            raise ACPError(Error.model_validate(response.json()))

    def _create_url(self, endpoint: str, base_url: httpx.URL | str | None) -> httpx.URL:
        merge_url = httpx.URL(endpoint)
        base_url = httpx.URL(base_url or self._client.base_url)

        if not merge_url.is_relative_url:
            raise ValueError("Endpoint must be a relative URL")

        if not base_url.raw_path.endswith(b"/"):
            base_url = base_url.copy_with(raw_path=base_url.raw_path + b"/")
        merge_raw_path = base_url.raw_path + merge_url.raw_path.lstrip(b"/")
        return base_url.copy_with(raw_path=merge_raw_path)
