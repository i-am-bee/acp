import { setTimeout } from "node:timers/promises";
import { spawn } from "node:child_process";
import { join } from "node:path";
import { describe, test, expect, beforeAll, afterAll } from "vitest";
import waitOn from "wait-on";
import { Client } from "../../src/client/client";
import {
  Agent,
  Message,
  MessageAwaitResume,
  Event,
} from "../../src/models/models";

describe("client", () => {
  const baseUrl = "http://localhost:8000";
  let serverProcess: ReturnType<typeof spawn>;

  beforeAll(async () => {
    serverProcess = spawn(
      "uv",
      ["run", "--no-sync", join(import.meta.dirname, "run_server.py")],
      { shell: true }
    );

    serverProcess.stderr?.on("data", (data) => {
      console.error(`stderr: ${data}`);
    });

    serverProcess.on("exit", (code, signal) => {
      console.log(`[ACP SERVER] exited code=${code}, signal=${signal}`);
    });

    try {
      await waitOn({
        resources: [`http-get://localhost:8000/ping`],
        timeout: 29000,
      });
    } catch (e) {
      console.error(e);
      throw new Error("Failed to start ACP server for tests");
    }
  }, 30000);

  afterAll(() => {
    serverProcess?.kill();
  });

  const createClient = () => new Client({ baseUrl });

  describe("discovery", () => {
    test("ping doesn't throw", async () => {
      const client = createClient();

      await expect(client.ping()).resolves.toBeUndefined();
    });

    test("agents list returns agents", async () => {
      const client = createClient();

      const agents = await client.agents();
      expect(agents.length).toBeGreaterThan(0);

      for (const agent of agents) {
        expect(agent).toSatisfy((agent) => Agent.safeParse(agent).success);
      }
    });

    test("have echo agent and name is correct", async () => {
      const client = createClient();
      const agentName = "echo";

      const agent = await client.agent(agentName);

      expect(agent).toSatisfy((agent) => Agent.safeParse(agent).success);
      expect(agent.name).toBe(agentName);
    });
  });

  describe("runs", () => {
    const input = [Message.parse({ parts: [{ content: "Hello!" }] })];
    const awaitResume = MessageAwaitResume.parse({
      type: "message",
      message: { parts: [] },
    });

    test("sync run is completed", async () => {
      const client = createClient();

      const run = await client.runSync("echo", input);

      expect(run.status).toBe("completed");
      expect(run.output).toHaveLength(1);
      expect(run.output).toContainEqual(
        expect.objectContaining({
          parts: [
            expect.objectContaining({
              content: "Hello!",
              content_type: "text/plain",
            }),
          ],
        })
      );
    });

    test("async run is only in created status", async () => {
      const client = createClient();

      const run = await client.runAsync("echo", input);

      expect(run.status).toBe("created");
    });

    test("async run changes status until completed", async () => {
      const client = createClient();

      let run = await client.runAsync("echo", input);
      while (run.status === "created" || run.status === "in-progress") {
        run = await client.runStatus(run.run_id);
      }
      expect(run.status).toBe("completed");
    });

    test("stream run, generates created and completed events", async () => {
      const client = createClient();

      const events: Event[] = [];
      for await (const event of client.runStream("echo", input)) {
        events.push(event);
      }

      expect(events.at(0)?.type).toBe("run.created");
      expect(events.at(-1)?.type).toBe("run.completed");
    });

    test("run events contain created and completed", async () => {
      const client = createClient();

      const run = await client.runSync("echo", input);
      const events = await client.runEvents(run.run_id);

      expect(events.at(0)?.type).toBe("run.created");
      expect(events.at(-1)?.type).toBe("run.completed");
    });

    test.for(["failer", "raiser"])("%s run fails", async (agentName) => {
      const client = createClient();

      const run = await client.runSync(agentName, input);

      expect(run.status).toBe("failed");
      expect(run.error).toBeDefined();
      expect(run.error?.code).toBe("invalid_input");
    });

    test.for(["awaiter", "slow_echo"])(
      "%s run cancel works",
      async (agentName) => {
        const client = createClient();

        let run = await client.runAsync(agentName, input);
        run = await client.runCancel(run.run_id);

        expect(run.status).toBe("cancelling");

        await setTimeout(1000);

        run = await client.runStatus(run.run_id);
        expect(run.status).toBe("cancelled");
      }
    );

    test("run cancel during a streaming works", async () => {
      const client = createClient();

      let lastEvent: Event | undefined;
      for await (const event of client.runStream("slow_echo", input)) {
        lastEvent = event;
        if (event.type === "run.created") {
          const run = await client.runCancel(event.run.run_id);
          expect(run.status).toBe("cancelling");
        }
      }
      expect(lastEvent?.type).toBe("run.cancelled");
    });

    test("awaiter run is resumed sync", async () => {
      const client = createClient();

      let run = await client.runSync("awaiter", input);

      expect(run.status).toBe("awaiting");
      expect(run.await_request).toBeDefined();

      run = await client.runResumeSync(run.run_id, awaitResume);

      expect(run.status).toBe("completed");
    });

    test("awaiter run is resumed async", async () => {
      const client = createClient();

      let run = await client.runSync("awaiter", input);

      expect(run.status).toBe("awaiting");
      expect(run.await_request).toBeDefined();

      run = await client.runResumeAsync(run.run_id, awaitResume);
      expect(run.status).toBe("in-progress");
    });

    test("awaiter run is resumed stream", async () => {
      const client = createClient();

      let run = await client.runSync("awaiter", input);

      expect(run.status).toBe("awaiting");
      expect(run.await_request).toBeDefined();

      const events: Event[] = [];
      for await (const event of client.runResumeStream(
        run.run_id,
        awaitResume
      )) {
        events.push(event);
      }

      expect(events.at(0)?.type).toBe("run.in-progress");
      expect(events.at(-1)?.type).toBe("run.completed");
    });

    test("sessions work", async () => {
      const client = createClient();

      await client.withSession(async (session) => {
        let run = await session.runSync("history_echo", input);
        expect(run.output).toHaveLength(1);
        run = await session.runSync("history_echo", input);
        expect(run.output).toHaveLength(3);
      });
    });
  });
});
