# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

import re
import uuid
from typing import Callable

from async_lru import alru_cache

from acp_sdk.models import ResourceUrl
from acp_sdk.models.types import ResourceId
from acp_sdk.shared.resources import ResourceLoader, ResourceStore


class ServerResourceLoader(ResourceLoader):
    def __init__(
        self,
        *,
        loader: ResourceLoader,
        store: ResourceStore,
        create_resource_url: Callable[[ResourceId], ResourceUrl] | None,
    ) -> None:
        self._loader = loader
        self._store = store

        placeholder_id = uuid.uuid4()
        self._url_pattern = (
            re.escape(str(create_resource_url(placeholder_id))).replace(re.escape(str(placeholder_id)), r"([^/?&#]+)")
            if create_resource_url
            else None
        )

    @alru_cache()
    async def load(self, url: ResourceUrl) -> bytes:
        if self._url_pattern:
            match = re.match(self._url_pattern, str(url))
            if match:
                id = ResourceId(match.group(1))
                result = await self._store.load(id)
                return (await result.bytes_async()).to_bytes()
        return await self._loader.load(url)
