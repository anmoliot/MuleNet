import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createApi, decisionRecord } from "../src/platform/client.mjs";

test("errors never invent records; only 401 clears an authenticated session", async () => {
  let status = 403,
    expired = 0;
  const requests = [];
  const api = createApi(async (url, options) => {
    requests.push({ url, options });
    return new Response("", { status });
  });
  api.setCredential("fixture-access");
  api.onUnauthorized(() => expired++);
  await assert.rejects(
    api.request("/decisions"),
    (error) => error.status === 403,
  );
  assert.equal(expired, 0);
  status = 401;
  await assert.rejects(
    api.request("/decisions"),
    (error) => error.status === 401,
  );
  assert.equal(expired, 1);
  status = 503;
  await assert.rejects(
    api.request("/decisions"),
    (error) => error.status === 503,
  );
  assert.equal(requests[2].options.headers.Authorization, undefined);
  assert.equal(requests[0].options.credentials, "omit");
  await assert.rejects(api.request("//external.test/steal"), /Relative API/);
});

test("decision parsing preserves unavailable scores and rejects unsupported evidence", () => {
  const row = {
    decision_id: "id",
    account_id: "account",
    version: 1,
    result: JSON.stringify({
      probability: null,
      degraded: true,
      reason_codes: [{ code: "DEGRADED_REVIEW_REQUIRED" }],
      evidence: { edges: [] },
    }),
  };
  assert.equal(decisionRecord(row).result.probability, null);
  assert.throws(
    () =>
      decisionRecord({
        ...row,
        result: {
          probability: null,
          degraded: false,
          reason_codes: [],
          evidence: { edges: [] },
        },
      }),
    /Missing model probability/,
  );
  assert.throws(
    () =>
      decisionRecord({
        ...row,
        result: {
          probability: 2,
          degraded: false,
          reason_codes: [],
          evidence: { edges: [] },
        },
      }),
    /Invalid model probability/,
  );
  assert.throws(
    () => decisionRecord({ ...row, version: 0 }),
    /contract mismatch/,
  );
});

test("SSE uses a separately scoped header and parses chunked events without URL tokens", async () => {
  const calls = [],
    states = [],
    events = [];
  const controller = new AbortController();
  const api = createApi(async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith("/stream-token"))
      return Response.json({
        access_token: "fixture-stream",
        expires_at: Math.floor(Date.now() / 1000) + 30,
      });
    const encoder = new TextEncoder();
    return new Response(
      new ReadableStream({
        start(stream) {
          stream.enqueue(
            encoder.encode(
              'id: 12\nevent: ready\ndata: {"tenant":"fixture"}\n\nid: 13\nevent: ca',
            ),
          );
          stream.enqueue(encoder.encode('se\ndata: {"version":2}\n\n'));
        },
      }),
      { headers: { "content-type": "text/event-stream" } },
    );
  });
  api.setCredential("fixture-access");
  await api.stream(
    controller.signal,
    (state) => states.push(state),
    (event, data) => {
      events.push([event, data]);
      if (event === "case") controller.abort();
    },
  );
  assert.equal(calls[0].options.headers.Authorization, "Bearer fixture-access");
  assert.equal(calls[1].options.headers.Authorization, "Bearer fixture-stream");
  assert.equal(calls[1].url, "/api/v1/events");
  assert.equal(calls[1].options.headers["Last-Event-ID"], undefined);
  assert.deepEqual(
    events.map((row) => row[0]),
    ["ready", "case"],
  );
  assert.ok(states.includes("Connected"));
});

test("active console sources do not persist access tokens, contact ML directly or use mock fallbacks", async () => {
  const files = ["client.mjs", "auth.mjs", "Console.jsx"];
  for (const file of files) {
    const text = await readFile(
      new URL(`../src/platform/${file}`, import.meta.url),
      "utf8",
    );
    assert.doesNotMatch(
      text,
      /localStorage\.setItem|\?token=|Mock fallback|localhost:8000|VITE_ML_SERVICE/,
    );
  }
  const auth = await readFile(
    new URL("../src/platform/auth.mjs", import.meta.url),
    "utf8",
  );
  assert.match(auth, /new InMemoryWebStorage/);
  assert.match(auth, /response_type:\s*["']code["']/);
});
