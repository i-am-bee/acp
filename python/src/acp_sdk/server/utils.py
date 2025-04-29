import asyncio
from collections.abc import AsyncGenerator, Coroutine
from typing import Any, Callable

import httpx
import requests
from pydantic import BaseModel

from acp_sdk.server.bundle import RunBundle
from acp_sdk.server.logging import logger


def encode_sse(model: BaseModel) -> str:
    return f"data: {model.model_dump_json()}\n\n"


async def stream_sse(bundle: RunBundle) -> AsyncGenerator[str]:
    async for event in bundle.stream():
        yield encode_sse(event)


async def async_request_with_retry(
    request_func: Callable[[httpx.AsyncClient], Coroutine[Any, Any, httpx.Response]],
    max_retries: int = 5,
    backoff_factor: float = 1,
) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        retries = 0
        while retries < max_retries:
            try:
                response = await request_func(client)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [429, 500, 502, 503, 504, 509]:
                    retries += 1
                    backoff = backoff_factor * (2 ** (retries - 1))
                    logger.debug(f"Request retry (try {retries}/{max_retries}), waiting {backoff} seconds...")
                    await asyncio.sleep(backoff)
                else:
                    logger.debug("A non-retryable error was encountered.")
                    raise
            except httpx.RequestError:
                retries += 1
                backoff = backoff_factor * (2 ** (retries - 1))
                logger.debug(f"Request retry (try {retries}/{max_retries}), waiting {backoff} seconds...")
                await asyncio.sleep(backoff)

        raise requests.exceptions.ConnectionError(f"Request failed after {max_retries} retries.")
