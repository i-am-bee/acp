import abc
import asyncio
import inspect
from collections.abc import AsyncGenerator, Coroutine, Generator
from concurrent.futures import ThreadPoolExecutor

import janus

from acp_sdk.models import (
    AgentName,
    Message,
    SessionId,
)
from acp_sdk.models.models import Metadata
from acp_sdk.server.context import Context
from acp_sdk.server.types import RunYield, RunYieldResume


class Agent(abc.ABC):
    @property
    def name(self) -> AgentName:
        return self.__class__.__name__

    @property
    def description(self) -> str:
        return ""

    @property
    def metadata(self) -> Metadata:
        return Metadata()

    @abc.abstractmethod
    def run(
        self, inputs: list[Message], context: Context
    ) -> (
        AsyncGenerator[RunYield, RunYieldResume] | Generator[RunYield, RunYieldResume] | Coroutine[RunYield] | RunYield
    ):
        pass

    async def execute(
        self, inputs: list[Message], session_id: SessionId | None, executor: ThreadPoolExecutor
    ) -> AsyncGenerator[RunYield, RunYieldResume]:
        yield_queue: janus.Queue[RunYield] = janus.Queue()
        yield_resume_queue: janus.Queue[RunYieldResume] = janus.Queue()

        context = Context(
            session_id=session_id, executor=executor, yield_queue=yield_queue, yield_resume_queue=yield_resume_queue
        )

        if inspect.isasyncgenfunction(self.run):
            run = asyncio.create_task(self._run_async_gen(inputs, context))
        elif inspect.iscoroutinefunction(self.run):
            run = asyncio.create_task(self._run_coro(inputs, context))
        elif inspect.isgeneratorfunction(self.run):
            run = asyncio.get_running_loop().run_in_executor(executor, self._run_gen, inputs, context)
        else:
            run = asyncio.get_running_loop().run_in_executor(executor, self._run_func, inputs, context)

        try:
            while True:
                value = yield await yield_queue.async_q.get()
                await yield_resume_queue.async_q.put(value)
        except janus.AsyncQueueShutDown:
            pass
        finally:
            await run  # Raise exceptions

    async def _run_async_gen(self, input: Message, context: Context) -> None:
        try:
            gen: AsyncGenerator[RunYield, RunYieldResume] = self.run(input, context)
            value = None
            while True:
                value = await context.yield_async(await gen.asend(value))
        except StopAsyncIteration:
            pass
        finally:
            context.shutdown()

    async def _run_coro(self, input: Message, context: Context) -> None:
        try:
            await context.yield_async(await self.run(input, context))
        finally:
            context.shutdown()

    def _run_gen(self, input: Message, context: Context) -> None:
        try:
            gen: Generator[RunYield, RunYieldResume] = self.run(input, context)
            value = None
            while True:
                value = context.yield_sync(gen.send(value))
        except StopIteration:
            pass
        finally:
            context.shutdown()

    def _run_func(self, input: Message, context: Context) -> None:
        try:
            context.yield_sync(self.run(input, context))
        finally:
            context.shutdown()
