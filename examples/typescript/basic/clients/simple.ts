/**
 * Copyright 2025 © BeeAI a Series of LF Projects, LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import { Client } from "acp-sdk";

const client = new Client({ baseUrl: "http://localhost:8000" });
const run = await client.runSync("echo", "Hello!");
run.output.forEach((message) => console.log(message));
