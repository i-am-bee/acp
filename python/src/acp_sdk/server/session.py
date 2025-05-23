import uuid

from pydantic import BaseModel, Field

from acp_sdk.models import Message, RunId, RunStatus, SessionId
from acp_sdk.server.executor import RunData
from acp_sdk.server.store import Store


class Session(BaseModel):
    id: SessionId = Field(default_factory=uuid.uuid4)
    runs: list[RunId] = []

    def append(self, run_id: RunId) -> None:
        self.runs.append(run_id)

    async def history(self, store: Store[RunData]) -> list[Message]:
        history = []
        for run_id in self.runs:
            run_data = await store.get(run_id)
            if run_data is not None and run_data.run.status == RunStatus.COMPLETED:
                history.extend(run_data.input)
                history.extend(run_data.run.output)
        return history
