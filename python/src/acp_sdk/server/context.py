import janus

from acp_sdk.models import SessionId
from acp_sdk.server.types import RunYield, RunYieldResume


class Context:
    def __init__(self, *, session_id: SessionId | None = None) -> None:
        self.session_id = session_id


class SyncContext(Context):
    def __init__(
        self,
        *,
        session_id: SessionId | None = None,
        yield_queue: janus.SyncQueue[RunYield],
        yield_resume_queue: janus.SyncQueue[RunYieldResume],
    ) -> None:
        super().__init__(session_id=session_id)
        self._yield_queue = yield_queue
        self._yield_resume_queue = yield_resume_queue

    def yield_(self, data: RunYield) -> RunYieldResume:
        self._yield_queue.put(data)
        return self._yield_resume_queue.get()
