# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0


import pytest
from acp_sdk.shared.resources import ResourceLoader
from pytest_httpx import HTTPXMock

mock_resource = {"url": "http://invalid/resource1", "content": b"foobar"}


@pytest.mark.asyncio
async def test_resource_loader_load(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=mock_resource["url"], method="GET", content=mock_resource["content"])

    resource_loader = ResourceLoader()
    resource = await resource_loader.load(mock_resource["url"])
    assert resource == mock_resource["content"]


@pytest.mark.asyncio
async def test_resource_loader_load_cache(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=mock_resource["url"], method="GET", content=mock_resource["content"])

    resource_loader = ResourceLoader()
    resource = await resource_loader.load(mock_resource["url"])
    resource = await resource_loader.load(mock_resource["url"])

    assert resource == mock_resource["content"]
