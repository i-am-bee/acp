import { trace } from '@opentelemetry/api';
import pkg from '../package.json' with { type: 'json' };

export function getTracer() {
  return trace.getTracer(pkg.name, pkg.version);
}
