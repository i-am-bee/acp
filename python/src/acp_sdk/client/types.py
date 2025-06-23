# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from acp_sdk.models import Message, MessagePart

Input = list[Message] | Message | list[MessagePart] | MessagePart | list[str] | str
