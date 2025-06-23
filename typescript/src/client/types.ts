/**
 * Copyright 2025 © BeeAI a Series of LF Projects, LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import { Message, MessagePart } from "../models/models.js";

export type Input = Message[] | Message | MessagePart[] | MessagePart | string[] | string;
