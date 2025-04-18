import asyncio
import logging
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor

from pydantic import ValidationError

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


class RunBundle:
    def __init__(
        self, *, agent: Agent, run: Run, inputs: list[Message], history: list[Message], executor: ThreadPoolExecutor
    ) -> None:
        self.agent = agent
        self.run = run
        self.inputs = inputs
        self.history = history

        self.stream_queue: asyncio.Queue[Event] = asyncio.Queue()

        self.await_queue: asyncio.Queue[AwaitResume] = asyncio.Queue(maxsize=1)
        self.await_or_terminate_event = asyncio.Event()

        self.task = asyncio.create_task(self._execute(inputs, executor=executor))

    async def stream(self) -> AsyncGenerator[Event]:
        while True:
            event = await self.stream_queue.get()
            if event is None:
                break
            yield event
            self.stream_queue.task_done()

    async def emit(self, event: Event) -> None:
        await self.stream_queue.put(event)

    async def await_(self) -> AwaitResume:
        await self.stream_queue.put(None)
        self.await_queue.empty()
        self.await_or_terminate_event.set()
        self.await_or_terminate_event.clear()
        resume = await self.await_queue.get()
        self.await_queue.task_done()
        return resume

    async def resume(self, resume: AwaitResume) -> None:
        self.stream_queue = asyncio.Queue()
        await self.await_queue.put(resume)
        self.run.status = RunStatus.IN_PROGRESS
        self.run.await_request = None

    async def cancel(self) -> None:
        self.task.cancel()
        self.run.status = RunStatus.CANCELLING
        self.run.await_request = None

    async def join(self) -> None:
        await self.await_or_terminate_event.wait()

    async def _execute(self, inputs: list[Message], *, executor: ThreadPoolExecutor) -> None:
        with get_tracer().start_as_current_span("run"):
            run_logger = logging.LoggerAdapter(logger, {"run_id": str(self.run.run_id)})

            in_message = False
            try:
                await self.emit(RunCreatedEvent(run=self.run))

                generator = self.agent.execute(
                    inputs=self.history + inputs, session_id=self.run.session_id, executor=executor
                )
                run_logger.info("Run started")

                self.run.status = RunStatus.IN_PROGRESS
                await self.emit(RunInProgressEvent(run=self.run))

                await_resume = None
                while True:
                    next = await generator.asend(await_resume)

                    if isinstance(next, MessagePart):
                        if not in_message:
                            self.run.outputs.append(Message(parts=[]))
                            in_message = True
                            await self.emit(MessageCreatedEvent(message=self.run.outputs[-1]))
                        self.run.outputs[-1].parts.append(next)
                        await self.emit(MessagePartEvent(part=next))
                    elif isinstance(next, Message):
                        if in_message:
                            await self.emit(MessageCompletedEvent(message=self.run.outputs[-1]))
                            in_message = False
                        self.run.outputs.append(next)
                        await self.emit(MessageCreatedEvent(message=next))
                        for part in next.parts:
                            await self.emit(MessagePartEvent(part=part))
                        await self.emit(MessageCompletedEvent(message=next))
                    elif isinstance(next, AwaitRequest):
                        self.run.await_request = next
                        self.run.status = RunStatus.AWAITING
                        await self.emit(RunAwaitingEvent(run=self.run))
                        run_logger.info("Run awaited")
                        await_resume = await self.await_()
                        await self.emit(RunInProgressEvent(run=self.run))
                        run_logger.info("Run resumed")
                    elif isinstance(next, Error):
                        raise ACPError(error=next)
                    elif next is None:
                        pass  # Do nothing
                    else:
                        try:
                            generic = AnyModel.model_validate(next)
                            await self.emit(GenericEvent(generic=generic))
                        except ValidationError:
                            raise TypeError("Invalid yield")
            except StopAsyncIteration:
                if in_message:
                    await self.emit(MessageCompletedEvent(message=self.run.outputs[-1]))
                self.run.status = RunStatus.COMPLETED
                await self.emit(RunCompletedEvent(run=self.run))
                run_logger.info("Run completed")
            except asyncio.CancelledError:
                self.run.status = RunStatus.CANCELLED
                await self.emit(RunCancelledEvent(run=self.run))
                run_logger.info("Run cancelled")
            except Exception as e:
                if isinstance(e, ACPError):
                    self.run.error = e.error
                else:
                    self.run.error = Error(code=ErrorCode.SERVER_ERROR, message=str(e))
                self.run.status = RunStatus.FAILED
                await self.emit(RunFailedEvent(run=self.run))
                run_logger.exception("Run failed")
                raise
            finally:
                self.await_or_terminate_event.set()
                await self.stream_queue.put(None)
