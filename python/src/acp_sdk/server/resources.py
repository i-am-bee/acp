import cachetools

from acp_sdk.models import ResourceUrl
from acp_sdk.models.types import ResourceId
from acp_sdk.shared.resources import ResourceLoader, ResourceStore


class ServerResourceLoader(ResourceLoader):
    def __init__(self, *, loader: ResourceLoader, store: ResourceStore, base_url: str | None) -> None:
        self._loader = loader
        self._store = store
        self._base_url = base_url

    @cachetools.func.lfu_cache
    async def load(self, url: ResourceUrl) -> bytes:
        if self._base_url and str(url).startswith(self._base_url):
            path_segments = url.path.split("/")
            if len(path_segments) > 0:
                id = ResourceId(path_segments[-1])
                result = await self._store.load(id)
                return (await result.bytes_async()).to_bytes()
        return await self._loader.load(url)
