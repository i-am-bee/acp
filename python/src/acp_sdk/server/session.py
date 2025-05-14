import uuid

from acp_sdk.models import Message, RunId, RunStatus, SessionId
from acp_sdk.server.executor import RunData
from acp_sdk.server.store import Store


class Session:
    def __init__(self, id: SessionId | None = None) -> None:
        self.id: SessionId = id or uuid.uuid4()
        self.runs: list[RunId] = []

    def append(self, run_id: RunId) -> None:
        self.runs.append(run_id)

    async def history(self, store: Store[RunData]) -> list[Message]:
        history = []
        for run_id in self.runs:
            bundle = await store.get(run_id)
            assert bundle is not None
            if bundle.run.status == RunStatus.COMPLETED:
                history.extend(bundle.input)
                history.extend(bundle.run.output)
        return history
