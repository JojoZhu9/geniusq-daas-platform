import { cp, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = resolve(root, "frontend", "dist");
const target = resolve(root, "dist");

await mkdir(target, { recursive: true });
await cp(source, target, { recursive: true, force: true });
await writeFile(resolve(target, "_redirects"), "/* /index.html 200\n", "utf8");
