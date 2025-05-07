from collections.abc import Awaitable
from datetime import timedelta
from typing import Callable

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


async def default_resource_url_factory(id: ResourceId, store: ObjectStore) -> ResourceUrl:
    if isinstance(store, (AzureStore, GCSStore, S3Store)):
        url = await obstore.sign_async(store, "GET", str(id), timedelta(hours=1))
        return ResourceUrl(url=url)
    elif isinstance(store, HTTPStore):
        return ResourceUrl(url=f"{store.url}/{id!s}")
    else:
        raise NotImplementedError("Unsupported store")


class ResourceStore:
    def __init__(
        self,
        *,
        store: ObjectStore,
        url_factory: Callable[[ResourceId, ObjectStore], Awaitable[ResourceUrl]] = default_resource_url_factory,
    ) -> None:
        self._store = store
        self.url_factory = url_factory

    async def load(self, id: ResourceId):  # noqa: ANN201
        result = await self._store.get_async(str(id))
        return result

    async def store(
        self,
        id: ResourceId,
        data: bytes,
    ) -> None:
        await self._store.put_async(str(id), data)

    async def get_resource_url(self, id: ResourceId) -> ResourceUrl:
        return await self.url_factory(id, self._store)
