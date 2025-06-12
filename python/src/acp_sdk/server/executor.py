import asyncio
import inspect
import logging
import uuid
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable, Self

import janus
from fastapi import Request
from pydantic import BaseModel, ValidationError

from acp_sdk.instrumentation import get_tracer
from acp_sdk.models import (
    ACPError,
    AnyModel,
    AwaitRequest,
    AwaitResume,
    Error,
    ErrorCode,
    Event,
    GenericEvent,
    Message,
    MessageCompletedEvent,
    MessageCreatedEvent,
    MessagePart,
    MessagePartEvent,
    ResourceId,
    ResourceUrl,
    Run,
    RunAwaitingEvent,
    RunCancelledEvent,
    RunCompletedEvent,
    RunCreatedEvent,
    RunFailedEvent,
    RunInProgressEvent,
    RunStatus,
    Session,
)
from acp_sdk.server.agent import AgentManifest
from acp_sdk.server.context import Context
from acp_sdk.server.logging import logger
from acp_sdk.server.store import Store
from acp_sdk.server.types import RunYield, RunYieldResume
from acp_sdk.shared import ResourceLoader, ResourceStore


class RunData(BaseModel):
    run: Run
    events: list[Event] = []

    @property
    def key(self) -> str:
        return str(self.run.run_id)

    async def watch(self, store: Store[Self], *, ready: asyncio.Event | None = None) -> AsyncIterator[Self]:
        async for data in store.watch(self.key, ready=ready):
            if data is None:
                raise RuntimeError("Missing data")
            yield data
            if data.run.status.is_terminal:
                break


class CancelData(BaseModel):
    pass


class Executor:
    def __init__(
        self,
        *,
        agent: AgentManifest,
        run_data: RunData,
        session: Session,
        executor: ThreadPoolExecutor,
        request: Request,
        run_store: Store[RunData],
        cancel_store: Store[CancelData],
        resume_store: Store[AwaitResume],
        session_store: Store[Session],
        resource_store: ResourceStore,
        resource_loader: ResourceLoader,
        create_resource_url: Callable[[ResourceId], Awaitable[ResourceUrl]],
    ) -> None:
        self.agent = agent
        self.session = session
        self.run_data = run_data
        self.executor = executor
        self.request = request

        self.run_store = run_store
        self.cancel_store = cancel_store
        self.resume_store = resume_store
        self.session_store = session_store
        self.resource_store = resource_store
        self.resource_loader = resource_loader

        self.create_resource_url = create_resource_url

        self.logger = logging.LoggerAdapter(logger, {"run_id": str(run_data.run.run_id)})

    def execute(self, input: list[Message], *, wait: asyncio.Event) -> None:
        self.task = asyncio.create_task(self._execute(input=input, executor=self.executor, wait=wait))
        self.watcher = asyncio.create_task(self._watch_for_cancellation())

    async def _push(self) -> None:
        await self.run_store.set(self.run_data.run.run_id, self.run_data)

    async def _emit(self, event: Event) -> None:
        freeze = event.model_copy(deep=True)
        self.run_data.events.append(freeze)
        await self._push()

    async def _await(self) -> AwaitResume:
        async for resume in self.resume_store.watch(self.run_data.key):
            if resume is not None:
                await self.resume_store.set(self.run_data.key, None)
                return resume

    async def _watch_for_cancellation(self) -> None:
        while not self.task.done():
            try:
                async for data in self.cancel_store.watch(self.run_data.key):
                    if data is not None:
                        self.task.cancel()
            except Exception:
                logger.warning("Cancellation watcher failed, restarting")

    async def _record_session(self, history: list[Message]) -> None:
        for message in history:
            id = uuid.uuid4()
            url = await self.create_resource_url(id)
            await self.resource_store.store(id, message.model_dump_json().encode())
            self.session.history.append(url)
        await self.session_store.set(self.session.id, self.session)

    async def _execute(self, input: list[Message], *, executor: ThreadPoolExecutor, wait: asyncio.Event) -> None:
        run_data = self.run_data
        with get_tracer().start_as_current_span("run"):
            in_message = False

            async def flush_message() -> None:
                nonlocal in_message
                if in_message:
                    message = run_data.run.output[-1]
                    message.completed_at = datetime.now(timezone.utc)
                    await self._emit(MessageCompletedEvent(message=message))
                    session_history.append(message)
                    in_message = False

            session_history = input.copy()
            try:
                await wait.wait()

                await self._emit(RunCreatedEvent(run=run_data.run))

                generator = self._execute_agent(
                    input=input,
                    session=self.session,
                    storage=self.resource_store,
                    loader=self.resource_loader,
                    executor=executor,
                    request=self.request,
                )
                self.logger.info("Run started")

                run_data.run.status = RunStatus.IN_PROGRESS
                await self._emit(RunInProgressEvent(run=run_data.run))

                await_resume = None
                while True:
                    next = await generator.asend(await_resume)

                    if isinstance(next, (MessagePart, str)):
                        if isinstance(next, str):
                            next = MessagePart(content=next)
                        if not in_message:
                            run_data.run.output.append(
                                Message(role=f"agent/{self.agent.name}", parts=[], completed_at=None)
                            )
                            in_message = True
                            await self._emit(MessageCreatedEvent(message=run_data.run.output[-1]))
                        run_data.run.output[-1].parts.append(next)
                        await self._emit(MessagePartEvent(part=next))
                    elif isinstance(next, Message):
                        await flush_message()
                        run_data.run.output.append(next.model_copy(update={"role": f"agent/{self.agent.name}"}))
                        await self._emit(MessageCreatedEvent(message=next))
                        for part in next.parts:
                            await self._emit(MessagePartEvent(part=part))
                        await self._emit(MessageCompletedEvent(message=next))
                        session_history.append(next)
                    elif isinstance(next, AwaitRequest):
                        run_data.run.await_request = next
                        run_data.run.status = RunStatus.AWAITING
                        await self._emit(RunAwaitingEvent(run=run_data.run))
                        self.logger.info("Run awaited")
                        await_resume = await self._await()
                        run_data.run.status = RunStatus.IN_PROGRESS
                        await self._emit(RunInProgressEvent(run=run_data.run))
                        self.logger.info("Run resumed")
                    elif isinstance(next, Error):
                        raise ACPError(error=next)
                    elif isinstance(next, BaseException):
                        raise next
                    elif next is None:
                        await flush_message()
                    elif isinstance(next, BaseModel):
                        await self._emit(GenericEvent(generic=AnyModel(**next.model_dump())))
                    else:
                        try:
                            generic = AnyModel.model_validate(next)
                            await self._emit(GenericEvent(generic=generic))
                        except ValidationError:
                            raise TypeError("Invalid yield")
            except StopAsyncIteration:
                await flush_message()
                run_data.run.status = RunStatus.COMPLETED
                run_data.run.finished_at = datetime.now(timezone.utc)
                try:
                    await self._record_session(session_history)
                except Exception as e:
                    self.logger.warning(f"Failed to record session: {e}")
                await self._emit(RunCompletedEvent(run=run_data.run))
                self.logger.info("Run completed")
            except asyncio.CancelledError:
                run_data.run.status = RunStatus.CANCELLED
                run_data.run.finished_at = datetime.now(timezone.utc)
                await self._emit(RunCancelledEvent(run=run_data.run))
                self.logger.info("Run cancelled")
            except Exception as e:
                if isinstance(e, ACPError):
                    run_data.run.error = e.error
                else:
                    run_data.run.error = Error(code=ErrorCode.SERVER_ERROR, message=str(e))
                run_data.run.status = RunStatus.FAILED
                run_data.run.finished_at = datetime.now(timezone.utc)
                await self._emit(RunFailedEvent(run=run_data.run))
                self.logger.exception("Run failed")

    async def _execute_agent(
        self,
        input: list[Message],
        session: Session,
        storage: ResourceStore,
        loader: ResourceLoader,
        executor: ThreadPoolExecutor,
        request: Request,
    ) -> AsyncGenerator[RunYield, RunYieldResume]:
        yield_queue: janus.Queue[RunYield] = janus.Queue()
        yield_resume_queue: janus.Queue[RunYieldResume] = janus.Queue()

        context = Context(
            session=session,
            store=storage,
            loader=loader,
            executor=executor,
            request=request,
            yield_queue=yield_queue,
            yield_resume_queue=yield_resume_queue,
        )

        if inspect.isasyncgenfunction(self.agent.run):
            run = asyncio.create_task(self._run_async_gen(input, context))
        elif inspect.iscoroutinefunction(self.agent.run):
            run = asyncio.create_task(self._run_coro(input, context))
        elif inspect.isgeneratorfunction(self.agent.run):
            run = asyncio.get_running_loop().run_in_executor(executor, self._run_gen, input, context)
        else:
            run = asyncio.get_running_loop().run_in_executor(executor, self._run_func, input, context)

        try:
            while not run.done() or yield_queue.async_q.qsize() > 0:
                value = yield await yield_queue.async_q.get()
                if isinstance(value, Exception):
                    raise value
                await yield_resume_queue.async_q.put(value)
        except janus.AsyncQueueShutDown:
            pass

    async def _run_async_gen(self, input: list[Message], context: Context) -> None:
        try:
            gen: AsyncGenerator[RunYield, RunYieldResume] = self.agent.run(input, context)
            value = None
            while True:
                value = await context.yield_async(await gen.asend(value))
        except StopAsyncIteration:
            pass
        except Exception as e:
            await context.yield_async(e)
        finally:
            context.shutdown()

    async def _run_coro(self, input: list[Message], context: Context) -> None:
        try:
            await context.yield_async(await self.agent.run(input, context))
        except Exception as e:
            await context.yield_async(e)
        finally:
            context.shutdown()

    def _run_gen(self, input: list[Message], context: Context) -> None:
        try:
            gen: Generator[RunYield, RunYieldResume] = self.agent.run(input, context)
            value = None
            while True:
                value = context.yield_sync(gen.send(value))
        except StopIteration:
            pass
        except Exception as e:
            context.yield_sync(e)
        finally:
            context.shutdown()

    def _run_func(self, input: list[Message], context: Context) -> None:
        try:
            context.yield_sync(self.agent.run(input, context))
        except Exception as e:
            context.yield_sync(e)
        finally:
            context.shutdown()
