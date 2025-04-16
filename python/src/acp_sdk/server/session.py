import uuid
from collections.abc import Iterator

from acp_sdk.models import Message, SessionId
from acp_sdk.models.models import RunStatus
from acp_sdk.server.bundle import RunBundle


class Session:
    def __init__(self) -> None:
        self.id: SessionId = uuid.uuid4()
        self.bundles: list[RunBundle] = []

    def append(self, bundle: RunBundle) -> None:
        self.bundles.append(bundle)

    def history(self) -> Iterator[Message]:
        for bundle in self.bundles:
            if bundle.run.status == RunStatus.COMPLETED:
                yield from bundle.inputs
                yield from bundle.run.outputs
