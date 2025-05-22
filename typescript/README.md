# Agent Communication Protocol SDK for Typescript

Agent Communication Protocol SDK for Typescript helps developers to serve and consume agents over the Agent Communication Protocol.

> [!Note]
> Currently, the SDK only contains ACP client and data models. Server implementation is coming soon!

## Installation

Install according to your package manager:

- `npm install acp-sdk`
- `yarn add acp-sdk`
- `pnpm install acp-sdk`
- ...

## Quickstart

> [!TIP]
> Make sure you have an ACP server running at port `8000`. The server is currently only implemented in [python](/python).

Run an agent:

```typescript
const client = new Client({ baseUrl: "http://localhost:8000" });
const run = await client.runSync("echo", "Hello!");
run.output.forEach((message) => console.log(message));
```


➡️ Explore more in our [examples library](/examples/typescript).
