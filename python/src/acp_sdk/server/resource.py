import uuid

from acp_sdk.models import ResourceUrl


class Resource:
    def __init__(
        self, *, id: uuid.UUID | None = None, url: ResourceUrl | None = None, mime_type: str, content: bytes
    ) -> None:
        self.id = id or uuid.uuid4()
        self.url = url
        self.mime_type = mime_type
        self.content = content
