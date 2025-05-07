import asyncio
from collections.abc import AsyncGenerator, Coroutine
from typing import Any, Callable

import httpx
import requests
from pydantic import BaseModel

from acp_sdk.models import RunStatus
from acp_sdk.server.executor import RunData
from acp_sdk.server.logging import logger
from acp_sdk.server.store import Store


def encode_sse(model: BaseModel) -> str:
    return f"data: {model.model_dump_json()}\n\n"


async def watch_util_stop(
    run_data: RunData, store: Store[RunData], *, ready: asyncio.Event | None = None
) -> AsyncGenerator[RunData]:
    async for data in run_data.watch(store, ready=ready):
        yield data
        if data.run.status == RunStatus.AWAITING:
            break


async def wait_util_stop(run_data: RunData, store: Store[RunData], *, ready: asyncio.Event | None = None) -> RunData:
    data = run_data
    async for latest_data in watch_util_stop(run_data, store, ready=ready):
        data = latest_data
    return data


async def stream_sse(
    run_data: RunData, store: Store[RunData], idx: int, *, ready: asyncio.Event | None = None
) -> AsyncGenerator[str]:
    next_event_idx = idx
    async for data in watch_util_stop(run_data, store, ready=ready):
        new_events = data.events[next_event_idx:]
        next_event_idx = len(data.events)
        for event in new_events:
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
