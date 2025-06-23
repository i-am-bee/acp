/**
 * Copyright 2025 © BeeAI a Series of LF Projects, LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import { z } from "zod";

export const PlatformUIType = z.enum(["chat", "hands-off"]);

export const AgentToolInfo = z.object({
  name: z.string(),
  description: z.string().nullish(),
});

export const PlatformUIAnnotation = z.object({
  ui_type: PlatformUIType,
  user_greeting: z.string().nullish(),
  display_name: z.string().nullish(),
  tools: z.array(AgentToolInfo).default([]),
});
