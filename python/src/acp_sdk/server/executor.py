import asyncio
import logging
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Self

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
    Run,
    RunAwaitingEvent,
    RunCancelledEvent,
    RunCompletedEvent,
    RunCreatedEvent,
    RunFailedEvent,
    RunInProgressEvent,
    RunStatus,
)
from acp_sdk.server.agent import Agent
from acp_sdk.server.logging import logger
from acp_sdk.server.store import Store


class RunData(BaseModel):
    run: Run
    input: list[Message]
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
        agent: Agent,
        run_data: RunData,
        history: list[Message],
        executor: ThreadPoolExecutor,
        run_store: Store[RunData],
        cancel_store: Store[CancelData],
        resume_store: Store[AwaitResume],
    ) -> None:
        self.agent = agent
        self.history = history
        self.run_data = run_data
        self.executor = executor

        self.run_store = run_store
        self.cancel_store = cancel_store
        self.resume_store = resume_store

        self.logger = logging.LoggerAdapter(logger, {"run_id": str(run_data.run.run_id)})

    def execute(self, *, wait: asyncio.Event) -> None:
        self.task = asyncio.create_task(self._execute(self.run_data, executor=self.executor, wait=wait))
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

    async def _execute(self, run_data: RunData, *, executor: ThreadPoolExecutor, wait: asyncio.Event) -> None:
        with get_tracer().start_as_current_span("run"):
            in_message = False

            async def flush_message() -> None:
                nonlocal in_message
                if in_message:
                    message = run_data.run.output[-1]
                    message.completed_at = datetime.now(timezone.utc)
                    await self._emit(MessageCompletedEvent(message=message))
                    in_message = False

            try:
                await wait.wait()

                await self._emit(RunCreatedEvent(run=run_data.run))

                generator = self.agent.execute(
                    input=self.history + run_data.input, session_id=run_data.run.session_id, executor=executor
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
                            run_data.run.output.append(Message(parts=[], completed_at=None))
                            in_message = True
                            await self._emit(MessageCreatedEvent(message=run_data.run.output[-1]))
                        run_data.run.output[-1].parts.append(next)
                        await self._emit(MessagePartEvent(part=next))
                    elif isinstance(next, Message):
                        await flush_message()
                        run_data.run.output.append(next)
                        await self._emit(MessageCreatedEvent(message=next))
                        for part in next.parts:
                            await self._emit(MessagePartEvent(part=part))
                        await self._emit(MessageCompletedEvent(message=next))
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
