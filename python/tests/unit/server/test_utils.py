# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

import pytest
from acp_sdk.models import AgentManifest
from acp_sdk.server.utils import agent_name_to_message_role


@pytest.mark.parametrize(
    "agent,role",
    [
        [AgentManifest(name="foo"), "agent/foo"],
        [AgentManifest(name="Foo"), "agent/Foo"],
        [AgentManifest(name="foo-bar-1"), "agent/foo-bar-1"],
    ],
)
def test_agent_name_to_message_role(agent: AgentManifest, role: str) -> None:
    assert agent_name_to_message_role(agent.name) == role


def test_invalid_agent_name_to_message_role() -> None:
    assert agent_name_to_message_role("Foo Bar") == "agent"
