from datetime import timedelta

import cachetools
import cachetools.func
import httpx
import obstore
from obstore.store import AzureStore, GCSStore, HTTPStore, ObjectStore, S3Store

from acp_sdk.models.types import ResourceId, ResourceUrl


class ResourceLoader:
    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(follow_redirects=False)

    @cachetools.func.lfu_cache
    async def load(self, url: ResourceUrl) -> bytes:
        response = await self._client.get(str(url))
        response.raise_for_status()
        return await response.aread()


class ResourceStore:
    def __init__(self, *, store: ObjectStore, presigned_url_expiration: timedelta = timedelta(days=7)) -> None:
        self._store = store
        self._presigned_url_expiration = presigned_url_expiration

    async def load(self, id: ResourceId):  # noqa: ANN201
        result = await self._store.get_async(str(id))
        return result

    async def store(
        self,
        id: ResourceId,
        data: bytes,
    ) -> None:
        await self._store.put_async(str(id), data)

    async def url(self, id: ResourceId) -> ResourceUrl:
        if isinstance(self._store, (AzureStore, GCSStore, S3Store)):
            url = await obstore.sign_async(self._store, "GET", str(id), self._presigned_url_expiration)
            return ResourceUrl(url=url)
        elif isinstance(self._store, HTTPStore):
            return ResourceUrl(url=f"{self._store.url}/{id!s}")
        else:
            raise NotImplementedError("Unsupported store")
