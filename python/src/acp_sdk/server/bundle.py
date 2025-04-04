import asyncio
import logging
from acp_sdk.server.agent import Agent
from acp_sdk.models import (
    ACPError,
    AnyModel,
    Await,
    AwaitEvent,
    CancelledEvent,
    CompletedEvent,
    CreatedEvent,
    FailedEvent,
    GenericEvent,
    Message,
    MessageEvent,
    Run,
    AwaitResume,
    RunEvent,
    RunStatus,
)
from acp_sdk.server.context import Context
from pydantic import BaseModel


logger = logging.getLogger("uvicorn.error")


class RunBundle:
    def __init__(self, *, agent: Agent, run: Run, task: asyncio.Task | None = None):
        self.agent = agent
        self.run = run
        self.task = task

        self.stream_queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        self.composed_message = Message()

        self.await_queue: asyncio.Queue[AwaitResume] = asyncio.Queue(maxsize=1)
        self.await_or_terminate_event = asyncio.Event()

    async def stream(self):
        try:
            while True:
                event = await self.stream_queue.get()
                yield event
                self.stream_queue.task_done()
        except asyncio.QueueShutDown:
            pass

    async def emit(self, event: RunEvent):
        await self.stream_queue.put(event)

    async def await_(self) -> AwaitResume:
        self.stream_queue.shutdown()
        self.await_queue.empty()
        self.await_or_terminate_event.set()
        self.await_or_terminate_event.clear()
        resume = await self.await_queue.get()
        self.await_queue.task_done()
        return resume

    async def resume(self, resume: AwaitResume):
        self.stream_queue = asyncio.Queue()
        await self.await_queue.put(resume)

    async def join(self):
        await self.await_or_terminate_event.wait()

    async def execute(self, input: Message):
        run_logger = logging.LoggerAdapter(logger, {"run_id": self.run.run_id})

        await self.emit(CreatedEvent(run=self.run))
        try:
            self.run.session_id = await self.agent.session(self.run.session_id)
            run_logger.info("Session loaded")

            generator = self.agent.run(
                input=input, context=Context(session_id=self.run.session_id)
            )
            run_logger.info("Run started")

            await_resume = None
            while True:
                self.run.status = RunStatus.IN_PROGRESS
                next = await generator.asend(await_resume)
                if isinstance(next, Message):
                    self.composed_message += next
                    await self.emit(MessageEvent(run_id=self.run.run_id, message=next))
                elif isinstance(next, Await):
                    self.run.await_ = next
                    self.run.status = RunStatus.AWAITING
                    await self.emit(
                        AwaitEvent.model_validate(
                            {
                                "run_id": self.run.run_id,
                                "type": "await",
                                "await": next,
                            }
                        )
                    )
                    run_logger.info("Run awaited")
                    await_resume = await self.await_()
                    run_logger.info("Run resumed")
                elif isinstance(next, AnyModel):
                    await self.emit(GenericEvent(run_id=self.run.run_id, generic=next))
                else:
                    raise TypeError("Not a pydantic model")
        except StopAsyncIteration:
            self.run.output = self.composed_message
            self.run.status = RunStatus.COMPLETED
            await self.emit(CompletedEvent(run=self.run))
            run_logger.info("Run completed")
        except asyncio.CancelledError:
            self.run.status = RunStatus.CANCELLED
            await self.emit(CancelledEvent(run=self.run))
            run_logger.info("Run cancelled")
        except Exception as e:
            self.run.error = ACPError(code="unspecified", message=str(e))
            self.run.status = RunStatus.FAILED
            await self.emit(FailedEvent(run=self.run))
            run_logger.exception("Run failed")
        finally:
            self.await_or_terminate_event.set()
            self.stream_queue.shutdown()
