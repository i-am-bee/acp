from concurrent.futures import ThreadPoolExecutor

import janus

from acp_sdk.models import SessionId
from acp_sdk.server.types import RunYield, RunYieldResume


class Context:
    def __init__(
        self,
        *,
        session_id: SessionId | None = None,
        executor: ThreadPoolExecutor,
        yield_queue: janus.Queue[RunYield],
        yield_resume_queue: janus.Queue[RunYieldResume],
    ) -> None:
        self.session_id = session_id
        self.executor = executor
        self._yield_queue = yield_queue
        self._yield_resume_queue = yield_resume_queue

    def yield_sync(self, value: RunYield) -> RunYieldResume:
        self._yield_queue.sync_q.put(value)
        return self._yield_resume_queue.sync_q.get()

    async def yield_async(self, value: RunYield) -> RunYieldResume:
        await self._yield_queue.async_q.put(value)
        return await self._yield_resume_queue.async_q.get()

    def shutdown(self) -> None:
        self._yield_queue.shutdown()
        self._yield_resume_queue.shutdown()
