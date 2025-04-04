from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiohttp
import aiohttp_sse_client.client

from acp_sdk.models import (
    Agent,
    AgentName,
    AgentReadResponse,
    AgentsListResponse,
    AwaitEvent,
    AwaitResume,
    CancelledEvent,
    CompletedEvent,
    FailedEvent,
    Message,
    RunCancelResponse,
    RunCreateRequest,
    Run,
    RunCreateResponse,
    RunEvent,
    RunId,
    RunMode,
    RunResumeRequest,
    RunResumeResponse,
)
from pydantic import TypeAdapter


class Client:
    def __init__(self, session: aiohttp.ClientSession):
        self._session = session

    async def agents(self) -> AsyncIterator[Agent]:
        async with self._session.get("/agents") as resp:
            response = AgentsListResponse.model_validate(await resp.json())
            for agent in response.agents:
                yield agent

    async def agent(self, *, name: AgentName) -> Agent:
        async with self._session.get(f"/agents/{name}") as resp:
            response = AgentReadResponse.model_validate(await resp.json())
            return response

    async def run_sync(self, *, agent: AgentName, input: Message) -> Run:
        async with self._session.post(
            "/runs",
            json=RunCreateRequest(
                agent_name=agent, input=input, mode=RunMode.SYNC
            ).model_dump(),
        ) as resp:
            return RunCreateResponse.model_validate(await resp.json())

    async def run_async(self, *, agent: AgentName, input: Message) -> Run:
        async with self._session.post(
            "/runs",
            json=RunCreateRequest(
                agent_name=agent, input=input, mode=RunMode.ASYNC
            ).model_dump(),
        ) as resp:
            return RunCreateResponse.model_validate(await resp.json())

    async def run_stream(
        self, *, agent: AgentName, input: Message
    ) -> AsyncIterator[RunEvent]:
        async with aiohttp_sse_client.client.EventSource(
            "/runs",
            session=self._session,
            option={"method": "POST"},
            json=RunCreateRequest(
                agent_name=agent, input=input, mode=RunMode.STREAM
            ).model_dump(),
        ) as event_source:
            async for event in event_source:
                print(event.data)
                event = TypeAdapter(RunEvent).validate_json(event.data)
                yield event
                if (
                    isinstance(event, CompletedEvent)
                    or isinstance(event, FailedEvent)
                    or isinstance(event, CancelledEvent)
                    or isinstance(event, AwaitEvent)
                ):
                    await event_source.close()
                    break

    async def run_status(self, *, run_id: RunId) -> Run:
        async with self._session.get(f"/runs/{run_id}") as resp:
            return Run.model_validate(await resp.json())

    async def run_cancel(self, *, run_id: RunId) -> Run:
        async with self._session.post(f"/runs/{run_id}/cancel") as resp:
            return RunCancelResponse.model_validate(await resp.json())

    async def run_resume_sync(self, *, run_id: RunId, await_: AwaitResume) -> Run:
        async with self._session.post(
            f"/runs/{run_id}",
            json=RunResumeRequest(await_=await_, mode=RunMode.SYNC).model_dump(),
        ) as resp:
            return RunResumeResponse.model_validate(await resp.json())

    async def run_resume_async(self, *, run_id: RunId, await_: AwaitResume) -> Run:
        async with self._session.post(
            f"/runs/{run_id}",
            json=RunResumeRequest(await_=await_, mode=RunMode.ASYNC).model_dump(),
        ) as resp:
            return RunResumeResponse.model_validate(await resp.json())

    async def run_resume_stream(
        self, *, run_id: RunId, await_: AwaitResume
    ) -> AsyncIterator[RunEvent]:
        async with aiohttp_sse_client.client.EventSource(
            f"/runs/{run_id}",
            session=self._session,
            option={"method": "POST"},
            json=RunResumeRequest(await_=await_, mode=RunMode.STREAM).model_dump(),
        ) as event_source:
            async for event in event_source:
                event = RunEvent.model_validate_json(event.data)
                yield event
                if (
                    isinstance(event, CompletedEvent)
                    or isinstance(event, FailedEvent)
                    or isinstance(event, CancelledEvent)
                    or isinstance(event, AwaitEvent)
                ):
                    await event_source.close()
                    break


@asynccontextmanager
async def create_client(url: str):
    async with aiohttp.ClientSession(url) as session:
        yield Client(session)
