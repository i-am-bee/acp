/**
 * Copyright 2025 © BeeAI a Series of LF Projects, LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import * as z from "zod";

export const ErrorCode = z.enum(["server_error", "invalid_input", "not_found"]);

export type ErrorCode = z.infer<typeof ErrorCode>;

export const ErrorModel = z.object({
  code: ErrorCode,
  message: z.string(),
});

export type ErrorModel = z.infer<typeof ErrorModel>;

