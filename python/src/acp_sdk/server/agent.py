import abc
import asyncio
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor

import janus

from acp_sdk.models import (
    AgentName,
    Message,
    SessionId,
)
from acp_sdk.models.models import Metadata
from acp_sdk.server.context import Context, SyncContext
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
        self, input: Message, context: Context, executor: ThreadPoolExecutor
    ) -> AsyncGenerator[RunYield, RunYieldResume]:
        pass

    async def session(self, session_id: SessionId | None) -> SessionId | None:
        if session_id:
            raise NotImplementedError()
        return None


class SyncAgent(Agent):
    @abc.abstractmethod
    def run_sync(self, input: Message, context: SyncContext, executor: ThreadPoolExecutor) -> RunYield | None:
        pass

    async def run(
        self, input: Message, context: Context, executor: ThreadPoolExecutor
    ) -> AsyncGenerator[RunYield, RunYieldResume]:
        yield_queue: janus.Queue[RunYield] = janus.Queue()
        yield_resume_queue: janus.Queue[RunYieldResume] = janus.Queue()

        run_future = asyncio.get_running_loop().run_in_executor(
            executor,
            self.run_sync,
            input,
            SyncContext(
                session_id=context.session_id,
                yield_queue=yield_queue.sync_q,
                yield_resume_queue=yield_resume_queue.sync_q,
            ),
            executor,
        )

        while True:
            yield_task = asyncio.create_task(yield_queue.async_q.get())
            done, _ = await asyncio.wait([yield_task, run_future], return_when=asyncio.FIRST_COMPLETED)
            if yield_task in done:
                resume = yield await yield_task
                await yield_resume_queue.async_q.put(resume)
            if run_future in done:
                yield await run_future
                break
