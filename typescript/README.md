# Agent Communication Protocol SDK for Typescript

Agent Communication Protocol SDK for Typescript helps developers to serve and consume agents over the Agent Communication Protocol.

## Installation

Install according to your package manager:

- `npm install acp-sdk`
- `yarn add acp-sdk`
- `pnpm install acp-sdk`
- ...

## Quickstart

Run an agent:

```typescript
const client = new Client({ baseUrl: "http://localhost:8000" });
const run = await client.runSync("echo", "Hello!");
run.output.forEach((message) => console.log(message));
```


➡️ Explore more in our [examples library](/examples/typescript).
