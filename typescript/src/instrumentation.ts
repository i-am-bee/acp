/**
 * Copyright 2025 © BeeAI a Series of LF Projects, LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import { trace } from '@opentelemetry/api';
import pkg from '../package.json' with { type: 'json' };

export function getTracer() {
  return trace.getTracer(pkg.name, pkg.version);
}
