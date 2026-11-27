import { preview } from "vite";
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile, writeFile, readdir, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

let input = "";
for await (const chunk of process.stdin) {
  input += chunk;
  if (input.length > 32768) throw new Error("Oversized test fixture");
}
const fixture = JSON.parse(input);
const backend = new URL(fixture.backend);
const octets = backend.hostname.split(".").map(Number);
const privateBridge =
  fixture.local_wsl_bridge === true &&
  octets.length === 4 &&
  octets.every(
    (value) => Number.isInteger(value) && value >= 0 && value < 256,
  ) &&
  (octets[0] === 10 ||
    (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) ||
    (octets[0] === 192 && octets[1] === 168));
if (
  backend.protocol !== "http:" ||
  (!["127.0.0.1", "localhost"].includes(backend.hostname) && !privateBridge) ||
  backend.username ||
  backend.password ||
  backend.search ||
  backend.hash ||
  backend.pathname !== "/"
)
  throw new Error(
    "Only loopback or an explicitly selected local WSL test bridge is permitted",
  );
const secrets = Object.values(fixture.passwords);
const redact = (text) =>
  secrets.reduce(
    (value, secret) => value.replaceAll(secret, "[REDACTED TEST CREDENTIAL]"),
    text,
  );
const sources = [];
async function walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = `${directory}/${entry.name}`;
    if (entry.isDirectory()) await walk(path);
    else sources.push(path);
  }
}
await walk("src/platform");
sources.push(
  "src/main.jsx",
  "index.html",
  "package.json",
  "package-lock.json",
  "vite.config.js",
  "playwright.platform.config.js",
  "tests/platform.spec.js",
  "scripts/run-platform-browser.mjs",
);
async function hashes() {
  return Object.fromEntries(
    await Promise.all(
      sources.sort().map(async (path) => [
        path,
        createHash("sha256")
          .update(await readFile(path))
          .digest("hex"),
      ]),
    ),
  );
}
const before = await hashes();
const build = spawnSync(
  process.execPath,
  ["node_modules/vite/bin/vite.js", "build"],
  { encoding: "utf8", timeout: 120000 },
);
if (build.status !== 0)
  throw new Error(
    `Console build failed: ${redact((build.stderr || "") + (build.stdout || ""))}`,
  );
const server = await preview({
  configFile: resolve("vite.config.js"),
  preview: {
    host: "127.0.0.1",
    port: 5181,
    strictPort: true,
    proxy: { "/api": { target: backend.origin, changeOrigin: true } },
  },
});
let outcome;
try {
  outcome = await new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [
        "node_modules/@playwright/test/cli.js",
        "test",
        "--config",
        "playwright.platform.config.js",
      ],
      {
        env: {
          ...process.env,
          PLATFORM_UI_URL: "http://127.0.0.1:5181",
          PLATFORM_BROWSER_CHANNEL:
            process.platform === "win32" ? "msedge" : "",
          MULENET_BROWSER_FIXTURE: JSON.stringify(fixture),
        },
      },
    );
    let stdout = "",
      stderr = "";
    const deadline = setTimeout(() => child.kill(), 300000);
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
      if (stdout.length > 16000000) child.kill();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
      if (stderr.length > 16000000) child.kill();
    });
    child.on("error", (error) => {
      clearTimeout(deadline);
      reject(error);
    });
    child.on("close", (status) => {
      clearTimeout(deadline);
      resolve({ status, stdout, stderr });
    });
  });
} finally {
  await new Promise((resolve) => server.httpServer.close(resolve));
}
await mkdir("../.tools", { recursive: true });
await writeFile(
  "../.tools/platform-browser.log",
  redact((outcome.stdout || "") + (outcome.stderr || "")),
);
const raw = redact(
  await readFile("../reports/frontend-browser-tests.json", "utf8"),
);
await writeFile("../reports/frontend-browser-tests.json", raw);
const result = JSON.parse(raw),
  after = await hashes();
const receipt = {
  data_provenance: "synthetic",
  scope:
    "Real Spring HTTP + Kafka/Postgres/Redis/ML test stack; controlled ML outage creates the reviewed holds; no API mocking",
  browser: result.stats,
  source_sha256: before,
  source_unchanged: JSON.stringify(before) === JSON.stringify(after),
  exit_code: outcome.status,
};
receipt.pass =
  outcome.status === 0 &&
  receipt.source_unchanged &&
  result.stats.expected >= 4 &&
  result.stats.unexpected === 0 &&
  result.stats.skipped === 0;
await writeFile(
  "../reports/frontend-platform.json",
  JSON.stringify(receipt, null, 2) + "\n",
);
console.log(
  JSON.stringify({
    pass: receipt.pass,
    browser: result.stats,
    source_unchanged: receipt.source_unchanged,
  }),
);
if (!receipt.pass) process.exitCode = 1;
