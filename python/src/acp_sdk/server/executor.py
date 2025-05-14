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
from acp_sdk.server.store.store import Store


class RunData(BaseModel):
    run: Run
    input: list[Message]
    events: list[Event] = []
    await_resume: AwaitResume | None = None

    async def watch(self, store: Store[Self]) -> AsyncIterator[Self]:
        async for data in store.watch(self.run.run_id):
            yield data
            if data.run.status.is_terminal:
                break


class Executor:
    def __init__(
        self,
        *,
        agent: Agent,
        run_data: RunData,
        history: list[Message],
        executor: ThreadPoolExecutor,
        store: Store[RunData],
    ) -> None:
        self.agent = agent
        self.run_data = run_data
        self.history = history

        self.store = store

        self.task = asyncio.create_task(self._execute(self.run_data.input, executor=executor))
        self.watcher = asyncio.create_task(self._watch())

    async def _sync(self) -> None:
        await self.store.set(self.run_data.run.run_id, self.run_data)

    async def _emit(self, event: Event) -> None:
        freeze = event.model_copy(deep=True)
        self.run_data.events.append(freeze)
        await self._sync()

    async def _await(self) -> AwaitResume:
        async for data in self.run_data.watch(self.store):
            resume = data.await_resume
            if resume is not None:
                data.await_resume = None
                return resume

    async def _watch(self) -> None:
        async for data in self.run_data.watch(self.store):
            if data.run.status == RunStatus.CANCELLING:
                self.task.cancel()

    async def _execute(self, input: list[Message], *, executor: ThreadPoolExecutor) -> None:
        with get_tracer().start_as_current_span("run"):
            run_logger = logging.LoggerAdapter(logger, {"run_id": str(self.run_data.run.run_id)})

            in_message = False

            async def flush_message() -> None:
                nonlocal in_message
                if in_message:
                    message = self.run_data.run.output[-1]
                    message.completed_at = datetime.now(timezone.utc)
                    await self._emit(MessageCompletedEvent(message=message))
                    in_message = False

            try:
                await self._emit(RunCreatedEvent(run=self.run_data.run))

                generator = self.agent.execute(
                    input=self.history + input, session_id=self.run_data.run.session_id, executor=executor
                )
                run_logger.info("Run started")

                self.run_data.run.status = RunStatus.IN_PROGRESS
                await self._emit(RunInProgressEvent(run=self.run_data.run))

                await_resume = None
                while True:
                    next = await generator.asend(await_resume)

                    if isinstance(next, (MessagePart, str)):
                        if isinstance(next, str):
                            next = MessagePart(content=next)
                        if not in_message:
                            self.run_data.run.output.append(Message(parts=[], completed_at=None))
                            in_message = True
                            await self._emit(MessageCreatedEvent(message=self.run_data.run.output[-1]))
                        self.run_data.run.output[-1].parts.append(next)
                        await self._emit(MessagePartEvent(part=next))
                    elif isinstance(next, Message):
                        await flush_message()
                        self.run_data.run.output.append(next)
                        await self._emit(MessageCreatedEvent(message=next))
                        for part in next.parts:
                            await self._emit(MessagePartEvent(part=part))
                        await self._emit(MessageCompletedEvent(message=next))
                    elif isinstance(next, AwaitRequest):
                        self.run_data.run.await_request = next
                        self.run_data.run.status = RunStatus.AWAITING
                        await self._emit(RunAwaitingEvent(run=self.run_data.run))
                        run_logger.info("Run awaited")
                        await_resume = await self._await()
                        await self._emit(RunInProgressEvent(run=self.run_data.run))
                        run_logger.info("Run resumed")
                    elif isinstance(next, Error):
                        raise ACPError(error=next)
                    elif isinstance(next, ACPError):
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
                self.run_data.run.status = RunStatus.COMPLETED
                self.run_data.run.finished_at = datetime.now(timezone.utc)
                await self._emit(RunCompletedEvent(run=self.run_data.run))
                run_logger.info("Run completed")
            except asyncio.CancelledError:
                self.run_data.run.status = RunStatus.CANCELLED
                self.run_data.run.finished_at = datetime.now(timezone.utc)
                await self._emit(RunCancelledEvent(run=self.run_data.run))
                run_logger.info("Run cancelled")
            except Exception as e:
                if isinstance(e, ACPError):
                    self.run_data.run.error = e.error
                else:
                    self.run_data.run.error = Error(code=ErrorCode.SERVER_ERROR, message=str(e))
                self.run_data.run.status = RunStatus.FAILED
                self.run_data.run.finished_at = datetime.now(timezone.utc)
                await self._emit(RunFailedEvent(run=self.run_data.run))
                run_logger.exception("Run failed")
                raise
            finally:
                if not self.task.done():
                    self.task.cancel()
