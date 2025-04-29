from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum

from cachetools import TTLCache
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from acp_sdk.models import (
    Agent as AgentModel,
)
from acp_sdk.models import (
    AgentName,
    AgentReadResponse,
    AgentsListResponse,
    Run,
    RunCancelResponse,
    RunCreateRequest,
    RunCreateResponse,
    RunEventsListResponse,
    RunId,
    RunMode,
    RunReadResponse,
    RunResumeRequest,
    RunResumeResponse,
    SessionId,
)
from acp_sdk.models.errors import ACPError
from acp_sdk.models.schemas import PingResponse
from acp_sdk.server.agent import Agent
from acp_sdk.server.bundle import RunBundle
from acp_sdk.server.errors import (
    RequestValidationError,
    StarletteHTTPException,
    acp_error_handler,
    catch_all_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from acp_sdk.server.session import Session
from acp_sdk.server.utils import stream_sse


class Headers(str, Enum):
    RUN_ID = "Run-ID"


def create_app(
    *agents: Agent,
    run_limit: int = 1000,
    run_ttl: timedelta = timedelta(hours=1),
    dependencies: list[Depends] | None = None,
) -> FastAPI:
    executor: ThreadPoolExecutor

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        nonlocal executor
        with ThreadPoolExecutor() as exec:
            executor = exec
            yield

    app = FastAPI(
        lifespan=lifespan,
        dependencies=dependencies,
    )

    FastAPIInstrumentor.instrument_app(app)

    agents: dict[AgentName, Agent] = {agent.name: agent for agent in agents}
    runs: TTLCache[RunId, RunBundle] = TTLCache(maxsize=run_limit, ttl=run_ttl, timer=datetime.now)
    sessions: TTLCache[SessionId, Session] = TTLCache(maxsize=run_limit, ttl=run_ttl, timer=datetime.now)

    app.exception_handler(ACPError)(acp_error_handler)
    app.exception_handler(StarletteHTTPException)(http_exception_handler)
    app.exception_handler(RequestValidationError)(validation_exception_handler)
    app.exception_handler(Exception)(catch_all_exception_handler)

    def find_run_bundle(run_id: RunId) -> RunBundle:
        bundle = runs.get(run_id)
        if not bundle:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return bundle

    def find_agent(agent_name: AgentName) -> Agent:
        agent = agents.get(agent_name, None)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        return agent

    @app.get("/agents")
    async def list_agents() -> AgentsListResponse:
        return AgentsListResponse(
            agents=[
                AgentModel(name=agent.name, description=agent.description, metadata=agent.metadata)
                for agent in agents.values()
            ]
        )

    @app.get("/agents/{name}")
    async def read_agent(name: AgentName) -> AgentReadResponse:
        agent = find_agent(name)
        return AgentModel(name=agent.name, description=agent.description, metadata=agent.metadata)

    @app.get("/ping")
    async def ping() -> PingResponse:
        return PingResponse()

    @app.post("/runs")
    async def create_run(request: RunCreateRequest) -> RunCreateResponse:
        agent = find_agent(request.agent_name)

        session = sessions.get(request.session_id, Session(id=request.session_id)) if request.session_id else Session()
        nonlocal executor
        bundle = RunBundle(
            agent=agent,
            run=Run(agent_name=agent.name, session_id=session.id),
            input=request.input,
            history=list(session.history()),
            executor=executor,
        )
        session.append(bundle)

        runs[bundle.run.run_id] = bundle
        sessions[session.id] = session

        headers = {Headers.RUN_ID: str(bundle.run.run_id)}

        match request.mode:
            case RunMode.STREAM:
                return StreamingResponse(
                    stream_sse(bundle),
                    headers=headers,
                    media_type="text/event-stream",
                )
            case RunMode.SYNC:
                await bundle.join()
                return JSONResponse(
                    headers=headers,
                    content=jsonable_encoder(bundle.run),
                )
            case RunMode.ASYNC:
                return JSONResponse(
                    status_code=status.HTTP_202_ACCEPTED,
                    headers=headers,
                    content=jsonable_encoder(bundle.run),
                )
            case _:
                raise NotImplementedError()

    @app.get("/runs/{run_id}")
    async def read_run(run_id: RunId) -> RunReadResponse:
        bundle = find_run_bundle(run_id)
        return bundle.run

    @app.get("/runs/{run_id}/events")
    async def list_run_events(run_id: RunId) -> RunEventsListResponse:
        bundle = find_run_bundle(run_id)
        return RunEventsListResponse(events=bundle.events)

    @app.post("/runs/{run_id}")
    async def resume_run(run_id: RunId, request: RunResumeRequest) -> RunResumeResponse:
        bundle = find_run_bundle(run_id)

        if bundle.run.await_request is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Run {run_id} has no await request")

        if bundle.run.await_request.type != request.await_resume.type:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Run {run_id} is expecting resume of type {bundle.run.await_request.type}",
            )

        await bundle.resume(request.await_resume)
        match request.mode:
            case RunMode.STREAM:
                return StreamingResponse(
                    stream_sse(bundle),
                    media_type="text/event-stream",
                )
            case RunMode.SYNC:
                await bundle.join()
                return bundle.run
            case RunMode.ASYNC:
                return JSONResponse(
                    status_code=status.HTTP_202_ACCEPTED,
                    content=jsonable_encoder(bundle.run),
                )
            case _:
                raise NotImplementedError()

    @app.post("/runs/{run_id}/cancel")
    async def cancel_run(run_id: RunId) -> RunCancelResponse:
        bundle = find_run_bundle(run_id)
        if bundle.run.status.is_terminal:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Run in terminal status {bundle.run.status} can't be cancelled",
            )
        await bundle.cancel()
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=jsonable_encoder(bundle.run))

    return app
