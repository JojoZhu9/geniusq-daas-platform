import { cp, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = resolve(root, "frontend", "dist");
const target = resolve(root, "dist");

await mkdir(target, { recursive: true });
await cp(source, target, { recursive: true, force: true });
await mkdir(resolve(target, ".openai"), { recursive: true });
await cp(resolve(root, ".openai", "hosting.json"), resolve(target, ".openai", "hosting.json"), { force: true });
await writeFile(resolve(target, "_redirects"), "/* /index.html 200\n", "utf8");
await mkdir(resolve(target, "server"), { recursive: true });
await writeFile(
  resolve(target, "server", "index.js"),
  `export default {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request);
    if (response.status !== 404) return response;
    const url = new URL(request.url);
    return env.ASSETS.fetch(new Request(new URL("/index.html", url), request));
  }
};
`,
  "utf8"
);
