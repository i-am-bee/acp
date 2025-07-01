import asyncio
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import timedelta
from enum import Enum

import httpx
import obstore.store
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.applications import AppType, Lifespan
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from obstore.exceptions import NotFoundError
from pydantic import AnyHttpUrl, ValidationError

from acp_sdk.models import (
    ACPError,
    AgentName,
    AgentReadResponse,
    AgentsListResponse,
    AwaitResume,
    PingResponse,
    ResourceId,
    ResourceUrl,
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
    RunStatus,
    Session,
    SessionId,
    SessionReadResponse,
)
from acp_sdk.models import (
    AgentManifest as AgentModel,
)
from acp_sdk.server.agent import AgentManifest
from acp_sdk.server.errors import (
    RequestValidationError,
    StarletteHTTPException,
    acp_error_handler,
    catch_all_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from acp_sdk.server.executor import CancelData, Executor, RunData
from acp_sdk.server.resources import ServerResourceLoader
from acp_sdk.server.store import MemoryStore, Store
from acp_sdk.server.utils import stream_sse, wait_util_stop
from acp_sdk.shared import ResourceLoader, ResourceStore


class Headers(str, Enum):
    RUN_ID = "Run-ID"


def create_app(
    *agents: AgentManifest,
    store: Store | None = None,
    resource_store: ResourceStore | None = None,
    resource_loader: ResourceLoader | None = None,
    forward_resources: bool = True,
    forward_base_url: AnyHttpUrl | str | None = None,
    lifespan: Lifespan[AppType] | None = None,
    dependencies: list[Depends] | None = None,
) -> FastAPI:
    if not forward_resources and (
        resource_store is None
        or isinstance(resource_store._store, (obstore.store.MemoryStore, obstore.store.LocalStore))
    ):
        raise ValueError("Resource forwarding must be enabled when resource store does not support HTTP URLs")

    if isinstance(forward_base_url, str):
        try:
            forward_base_url = AnyHttpUrl(forward_base_url)
        except ValidationError:
            raise ValueError("forward_base_url must be a valid http(s) url")

    executor: ThreadPoolExecutor
    client = httpx.AsyncClient()

    @asynccontextmanager
    async def internal_lifespan(app: FastAPI) -> AsyncGenerator[None]:
        nonlocal executor
        async with client:
            with ThreadPoolExecutor() as exec:
                executor = exec
                if not lifespan:
                    yield None
                else:
                    async with lifespan(app) as state:
                        yield state

    app = FastAPI(
        lifespan=internal_lifespan,
        dependencies=dependencies,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://agentcommunicationprotocol.dev"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    agents: dict[AgentName, AgentManifest] = {agent.name: agent for agent in agents}

    store = store or MemoryStore(limit=1000, ttl=timedelta(hours=1))
    run_store = store.as_store(model=RunData, prefix="run_")
    run_cancel_store = store.as_store(model=CancelData, prefix="run_cancel_")
    run_resume_store = store.as_store(model=AwaitResume, prefix="run_resume_")
    session_store = store.as_store(model=Session, prefix="session_")

    resource_loader = resource_loader or ResourceLoader(client=client)
    resource_store = resource_store or ResourceStore(store=obstore.store.MemoryStore())

    app.exception_handler(ACPError)(acp_error_handler)
    app.exception_handler(StarletteHTTPException)(http_exception_handler)
    app.exception_handler(RequestValidationError)(validation_exception_handler)
    app.exception_handler(Exception)(catch_all_exception_handler)

    async def find_run_data(run_id: RunId) -> RunData:
        run_data = await run_store.get(run_id)
        if not run_data:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if run_data.run.status.is_terminal:
            return run_data
        cancel_data = await run_cancel_store.get(run_data.key)
        if cancel_data is not None:
            run_data.run.status = RunStatus.CANCELLING
        return run_data

    def find_agent(agent_name: AgentName) -> AgentManifest:
        agent = agents.get(agent_name, None)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        return agent

    @app.get("/agents")
    async def list_agents() -> AgentsListResponse:
        return AgentsListResponse(
            agents=[
                AgentModel(
                    name=agent.name,
                    description=agent.description,
                    metadata=agent.metadata,
                    input_content_types=agent.input_content_types,
                    output_content_types=agent.output_content_types,
                )
                for agent in agents.values()
            ]
        )

    @app.get("/agents/{name}")
    async def read_agent(name: AgentName) -> AgentReadResponse:
        agent = find_agent(name)
        return AgentModel(
            name=agent.name,
            description=agent.description,
            metadata=agent.metadata,
            input_content_types=agent.input_content_types,
            output_content_types=agent.output_content_types,
        )

    @app.get("/ping")
    async def ping() -> PingResponse:
        return PingResponse()

    @app.post("/runs")
    async def create_run(request: RunCreateRequest, req: Request) -> RunCreateResponse:
        agent = find_agent(request.agent_name)

        if request.session_id and request.session and request.session_id != request.session.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID mismatch")

        def create_resource_url_forwarded(id: ResourceId) -> ResourceUrl:
            if not forward_resources:
                raise RuntimeError("Resource forwarding disabled")
            if forward_base_url:
                return ResourceUrl(
                    url=str(app.url_path_for("get_resource", resource_id=id).make_absolute_url(str(forward_base_url)))
                )
            return ResourceUrl(url=str(req.url_for("get_resource", resource_id=id)))

        async def create_resource_url(id: ResourceId) -> ResourceUrl:
            if forward_resources:
                return create_resource_url_forwarded(id)
            else:
                return await resource_store.url(id)

        server_resource_loader = ServerResourceLoader(
            loader=resource_loader,
            store=resource_store,
            create_resource_url=create_resource_url_forwarded if forward_resources else None,
        )

        session = request.session or (
            (await session_store.get(request.session_id) or Session(id=request.session_id))
            if request.session_id
            else Session()
        )
        session.loader = server_resource_loader
        session.store = resource_store

        nonlocal executor
        run_data = RunData(
            run=Run(
                agent_name=agent.name,
                session_id=session.id,
            )
        )
        await run_store.set(run_data.key, run_data)
        await session_store.set(session.id, session)

        headers = {Headers.RUN_ID: str(run_data.run.run_id)}
        ready = asyncio.Event()

        Executor(
            agent=agent,
            run_data=run_data,
            session=session,
            session_store=session_store,
            run_store=run_store,
            cancel_store=run_cancel_store,
            resume_store=run_resume_store,
            executor=executor,
            request=req,
            resource_store=resource_store,
            resource_loader=server_resource_loader,
            create_resource_url=create_resource_url,
        ).execute(request.input, wait=ready)

        match request.mode:
            case RunMode.STREAM:
                return StreamingResponse(
                    stream_sse(run_data, run_store, 0, ready=ready),
                    headers=headers,
                    media_type="text/event-stream",
                )
            case RunMode.SYNC:
                await wait_util_stop(run_data, run_store, ready=ready)
                return JSONResponse(
                    headers=headers,
                    content=jsonable_encoder(run_data.run),
                )
            case RunMode.ASYNC:
                ready.set()
                return JSONResponse(
                    status_code=status.HTTP_202_ACCEPTED,
                    headers=headers,
                    content=jsonable_encoder(run_data.run),
                )
            case _:
                raise NotImplementedError()

    @app.get("/runs/{run_id}")
    async def read_run(run_id: RunId) -> RunReadResponse:
        bundle = await find_run_data(run_id)
        return bundle.run

    @app.get("/runs/{run_id}/events")
    async def list_run_events(run_id: RunId) -> RunEventsListResponse:
        bundle = await find_run_data(run_id)
        return RunEventsListResponse(events=bundle.events)

    @app.post("/runs/{run_id}")
    async def resume_run(run_id: RunId, request: RunResumeRequest) -> RunResumeResponse:
        run_data = await find_run_data(run_id)

        if run_data.run.await_request is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Run {run_id} has no await request")

        if run_data.run.await_request.type != request.await_resume.type:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Run {run_id} is expecting resume of type {run_data.run.await_request.type}",
            )

        run_data.run.status = RunStatus.IN_PROGRESS
        await run_store.set(run_data.key, run_data)
        await run_resume_store.set(run_data.key, request.await_resume)

        match request.mode:
            case RunMode.STREAM:
                return StreamingResponse(
                    stream_sse(run_data, run_store, len(run_data.events)),
                    media_type="text/event-stream",
                )
            case RunMode.SYNC:
                run_data = await wait_util_stop(run_data, run_store)
                return run_data.run
            case RunMode.ASYNC:
                return JSONResponse(
                    status_code=status.HTTP_202_ACCEPTED,
                    content=jsonable_encoder(run_data.run),
                )
            case _:
                raise NotImplementedError()

    @app.post("/runs/{run_id}/cancel")
    async def cancel_run(run_id: RunId) -> RunCancelResponse:
        run_data = await find_run_data(run_id)
        if run_data.run.status.is_terminal:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Run in terminal status {run_data.run.status} can't be cancelled",
            )
        await run_cancel_store.set(run_data.key, CancelData())
        run_data.run.status = RunStatus.CANCELLING
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=jsonable_encoder(run_data.run))

    @app.get("/sessions/{session_id}")
    async def read_session(session_id: SessionId) -> SessionReadResponse:
        session = await session_store.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return session

    if forward_resources:

        @app.get("/resources/{resource_id}", name="get_resource")
        async def read_resource(resource_id: ResourceId) -> StreamingResponse:
            try:
                result = await resource_store.load(resource_id)
                return StreamingResponse(result)
            except NotFoundError:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Resource {resource_id} not found")

    return app
