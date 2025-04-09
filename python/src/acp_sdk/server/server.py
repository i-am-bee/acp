import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException, status
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
    RunId,
    RunMode,
    RunReadResponse,
    RunResumeRequest,
    RunResumeResponse,
    RunStatus,
)
from acp_sdk.models.errors import ACPError
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
from acp_sdk.server.logging import configure_logger as configure_logger_func
from acp_sdk.server.telemetry import configure_telemetry as configure_telemetry_func
from acp_sdk.server.utils import stream_sse


def create_app(*agents: Agent) -> FastAPI:
    app = FastAPI(title="acp-agents")

    FastAPIInstrumentor.instrument_app(app)

    agents: dict[AgentName, Agent] = {agent.name: agent for agent in agents}
    runs: dict[RunId, RunBundle] = {}

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

    @app.post("/runs")
    async def create_run(request: RunCreateRequest) -> RunCreateResponse:
        agent = find_agent(request.agent_name)
        bundle = RunBundle(
            agent=agent,
            run=Run(
                agent_name=agent.name,
                session_id=request.session_id,
            ),
        )

        bundle.task = asyncio.create_task(bundle.execute(request.input))
        runs[bundle.run.run_id] = bundle

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
                    content=bundle.run.model_dump(),
                )
            case _:
                raise NotImplementedError()

    @app.get("/runs/{run_id}")
    async def read_run(run_id: RunId) -> RunReadResponse:
        bundle = find_run_bundle(run_id)
        return bundle.run

    @app.post("/runs/{run_id}")
    async def resume_run(run_id: RunId, request: RunResumeRequest) -> RunResumeResponse:
        bundle = find_run_bundle(run_id)
        bundle.stream_queue = asyncio.Queue()  # TODO improve
        await bundle.await_queue.put(request.await_)
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
                    content=bundle.run.model_dump(),
                )
            case _:
                raise NotImplementedError()

    @app.post("/runs/{run_id}/cancel")
    async def cancel_run(run_id: RunId) -> RunCancelResponse:
        bundle = find_run_bundle(run_id)
        if bundle.run.status.is_terminal:
            raise HTTPException(
                status_code=403,
                detail=f"Run with terminal status {bundle.run.status} can't be cancelled",
            )
        bundle.task.cancel()
        bundle.run.status = RunStatus.CANCELLING
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=bundle.run.model_dump())

    return app


def serve(
    *agents: Agent, configure_logger: bool = True, configure_telemetry: bool = False, **kwargs: dict[str, Any]
) -> None:
    import uvicorn

    if configure_logger:
        configure_logger_func()
    if configure_telemetry:
        configure_telemetry_func()

    uvicorn.run(create_app(*agents), **kwargs)
