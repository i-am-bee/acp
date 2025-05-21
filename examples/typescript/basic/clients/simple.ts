import { Client } from "acp-sdk";

const client = new Client({ baseUrl: "http://localhost:8000" });
const run = await client.runSync("echo", "Hello!");
run.output.forEach((message) => console.log(message));
