import abc
import asyncio
import inspect
from collections.abc import AsyncGenerator, Coroutine, Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

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
        self, input: list[Message], context: Context
    ) -> (
        AsyncGenerator[RunYield, RunYieldResume] | Generator[RunYield, RunYieldResume] | Coroutine[RunYield] | RunYield
    ):
        pass

    async def execute(
        self, input: list[Message], session_id: SessionId | None, executor: ThreadPoolExecutor
    ) -> AsyncGenerator[RunYield, RunYieldResume]:
        yield_queue: janus.Queue[RunYield] = janus.Queue()
        yield_resume_queue: janus.Queue[RunYieldResume] = janus.Queue()

        context = Context(
            session_id=session_id, executor=executor, yield_queue=yield_queue, yield_resume_queue=yield_resume_queue
        )

        if inspect.isasyncgenfunction(self.run):
            run = asyncio.create_task(self._run_async_gen(input, context))
        elif inspect.iscoroutinefunction(self.run):
            run = asyncio.create_task(self._run_coro(input, context))
        elif inspect.isgeneratorfunction(self.run):
            run = asyncio.get_running_loop().run_in_executor(executor, self._run_gen, input, context)
        else:
            run = asyncio.get_running_loop().run_in_executor(executor, self._run_func, input, context)

        try:
            while True:
                value = yield await yield_queue.async_q.get()
                await yield_resume_queue.async_q.put(value)
        except janus.AsyncQueueShutDown:
            pass
        finally:
            await run  # Raise exceptions

    async def _run_async_gen(self, input: list[Message], context: Context) -> None:
        try:
            gen: AsyncGenerator[RunYield, RunYieldResume] = self.run(input, context)
            value = None
            while True:
                value = await context.yield_async(await gen.asend(value))
        except StopAsyncIteration:
            pass
        finally:
            context.shutdown()

    async def _run_coro(self, input: list[Message], context: Context) -> None:
        try:
            await context.yield_async(await self.run(input, context))
        finally:
            context.shutdown()

    def _run_gen(self, input: list[Message], context: Context) -> None:
        try:
            gen: Generator[RunYield, RunYieldResume] = self.run(input, context)
            value = None
            while True:
                value = context.yield_sync(gen.send(value))
        except StopIteration:
            pass
        finally:
            context.shutdown()

    def _run_func(self, input: list[Message], context: Context) -> None:
        try:
            context.yield_sync(self.run(input, context))
        finally:
            context.shutdown()


def agent(
    name: str | None = None,
    description: str | None = None,
    *,
    metadata: Metadata | None = None,
) -> Callable[[Callable], Agent]:
    """Decorator to create an agent."""

    def decorator(fn: Callable) -> Agent:
        signature = inspect.signature(fn)
        parameters = list(signature.parameters.values())

        if len(parameters) == 0:
            raise TypeError("The agent function must have at least 'input' argument")
        if len(parameters) > 2:
            raise TypeError("The agent function must have only 'input' and 'context' arguments")
        if len(parameters) == 2 and parameters[1].name != "context":
            raise TypeError("The second argument of the agent function must be 'context'")

        has_context_param = len(parameters) == 2

        class DecoratorAgentBase(Agent):
            @property
            def name(self) -> str:
                return name or fn.__name__

            @property
            def description(self) -> str:
                return description or inspect.getdoc(fn) or ""

            @property
            def metadata(self) -> Metadata:
                return metadata or Metadata()

        agent: Agent
        if inspect.isasyncgenfunction(fn):

            class AsyncGenDecoratorAgent(DecoratorAgentBase):
                async def run(self, input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
                    try:
                        gen: AsyncGenerator[RunYield, RunYieldResume] = (
                            fn(input, context) if has_context_param else fn(input)
                        )
                        value = None
                        while True:
                            value = yield await gen.asend(value)
                    except StopAsyncIteration:
                        pass

            agent = AsyncGenDecoratorAgent()
        elif inspect.iscoroutinefunction(fn):

            class CoroDecoratorAgent(DecoratorAgentBase):
                async def run(self, input: list[Message], context: Context) -> Coroutine[RunYield]:
                    return await (fn(input, context) if has_context_param else fn(input))

            agent = CoroDecoratorAgent()
        elif inspect.isgeneratorfunction(fn):

            class GenDecoratorAgent(DecoratorAgentBase):
                def run(self, input: list[Message], context: Context) -> Generator[RunYield, RunYieldResume]:
                    yield from (fn(input, context) if has_context_param else fn(input))

            agent = GenDecoratorAgent()
        else:

            class FuncDecoratorAgent(DecoratorAgentBase):
                def run(self, input: list[Message], context: Context) -> RunYield:
                    return fn(input, context) if has_context_param else fn(input)

            agent = FuncDecoratorAgent()

        return agent

    return decorator
