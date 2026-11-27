import { createParser } from "eventsource-parser";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function createApi(fetcher = globalThis.fetch.bind(globalThis)) {
  let credential = null;
  let unauthorized = () => {};
  const api = {
    setCredential(value) {
      credential = value;
    },
    onUnauthorized(callback) {
      unauthorized = callback;
    },
    async request(path, { method = "GET", body, signal } = {}) {
      if (!path.startsWith("/") || path.startsWith("//"))
        throw new Error("Relative API path required");
      const headers = { Accept: "application/json" };
      if (credential) headers.Authorization = `Bearer ${credential}`;
      if (body !== undefined) headers["Content-Type"] = "application/json";
      const response = await fetcher(`/api/v1${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: "omit",
        redirect: "error",
        cache: "no-store",
        signal: signal
          ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
          : AbortSignal.timeout(15000),
      });
      if (!response.ok) {
        if (response.status === 401 && credential) {
          credential = null;
          unauthorized();
        }
        const message =
          {
            400: "The request was rejected. Check the supplied fields.",
            401: "Authentication expired or credentials were rejected.",
            403: "Your role cannot perform this operation.",
            404: "The requested record was not found.",
            409: "The record changed. Reload before acting.",
            422: "The supplied values do not satisfy the contract.",
            429: "Request limit reached. Try again later.",
            503: "The service is unavailable. No substitute data is shown.",
          }[response.status] || `Service request failed (${response.status}).`;
        throw new ApiError(response.status, message);
      }
      if (
        response.status === 204 ||
        response.headers.get("content-length") === "0"
      )
        return null;
      const text = await response.text();
      const data = text ? JSON.parse(text) : null;
      if (method === "GET" && path === "/decisions") {
        if (!Array.isArray(data)) throw new Error("Invalid decisions response");
        return data.map(decisionRecord);
      }
      if (method === "GET" && /^\/decisions\/[^/]+$/.test(path))
        return decisionRecord(data);
      if (
        method === "GET" &&
        path === "/drift" &&
        (!Array.isArray(data?.windows) || data.automatic_action !== false)
      )
        throw new Error("Invalid tenant drift response");
      return data;
    },
    async stream(signal, onState, onEvent) {
      let cursor = null,
        failures = 0;
      while (!signal.aborted) {
        const connection = new AbortController();
        const stop = () => connection.abort();
        signal.addEventListener("abort", stop, { once: true });
        let deadline, reader;
        try {
          onState("Connecting");
          const scoped = await api.request("/stream-token", {
            method: "POST",
            signal,
          });
          if (!scoped?.access_token || !Number.isFinite(scoped.expires_at))
            throw new Error("Invalid stream credential contract");
          const remaining = scoped.expires_at * 1000 - Date.now();
          if (remaining <= 0 || remaining > 65000)
            throw new Error("Invalid stream lifetime");
          deadline = setTimeout(stop, remaining);
          const headers = {
            Authorization: `Bearer ${scoped.access_token}`,
            Accept: "text/event-stream",
          };
          if (cursor !== null) headers["Last-Event-ID"] = cursor;
          const response = await fetcher("/api/v1/events", {
            headers,
            signal: connection.signal,
            credentials: "omit",
            redirect: "error",
          });
          if (!response.ok)
            throw new ApiError(
              response.status,
              "Stream authorization or transport failed",
            );
          if (
            !response.headers
              .get("content-type")
              ?.startsWith("text/event-stream") ||
            !response.body
          )
            throw new Error("Invalid event stream contract");
          const parser = createParser({
            maxBufferSize: 1048576,
            onError(error) {
              throw error;
            },
            onEvent(event) {
              if (!["ready", "decision", "case"].includes(event.event)) return;
              const payload = JSON.parse(event.data);
              if (event.id !== undefined) {
                if (!/^\d{1,20}$/.test(event.id))
                  throw new Error("Invalid stream cursor");
                cursor = event.id;
              }
              if (event.event === "ready") {
                failures = 0;
                onState("Connected");
              }
              onEvent(event.event, payload);
            },
          });
          reader = response.body.getReader();
          const decoder = new TextDecoder();
          while (!signal.aborted) {
            const chunk = await reader.read();
            if (chunk.done) break;
            parser.feed(decoder.decode(chunk.value, { stream: true }));
          }
        } catch (error) {
          if (signal.aborted) return;
          if (error.status === 401 || error.status === 403) {
            onState("Authorization rejected");
            return;
          }
          if (!connection.signal.aborted) failures += 1;
          onState("Reconnecting");
          if (failures >= 6) {
            onState("Disconnected");
            return;
          }
        } finally {
          clearTimeout(deadline);
          connection.abort();
          signal.removeEventListener("abort", stop);
          if (reader) await reader.cancel().catch(() => {});
        }
        await delay(
          Math.min(1000 * 2 ** failures, 15000) + Math.random() * 300,
          signal,
        ).catch(() => {});
      }
    },
  };
  return api;
}

export function delay(milliseconds, signal) {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const finish = () => {
      signal.removeEventListener("abort", abort);
      resolve();
    };
    const timer = setTimeout(finish, milliseconds);
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    signal.addEventListener("abort", abort, { once: true });
  });
}

export function decisionRecord(row) {
  const result =
    typeof row.result === "string" ? JSON.parse(row.result) : row.result;
  if (
    !row.decision_id ||
    !row.account_id ||
    !Number.isInteger(row.version) ||
    row.version < 1 ||
    !result ||
    typeof result.degraded !== "boolean" ||
    !Array.isArray(result.reason_codes) ||
    !Array.isArray(result.evidence?.edges)
  )
    throw new Error("Decision contract mismatch; no substitute record");
  if (
    result.probability !== null &&
    (!Number.isFinite(result.probability) ||
      result.probability < 0 ||
      result.probability > 1)
  )
    throw new Error("Invalid model probability");
  if (result.probability === null && !result.degraded)
    throw new Error("Missing model probability without a degradation flag");
  if (
    !result.evidence.edges.every(
      (edge) =>
        typeof edge.source === "string" &&
        typeof edge.target === "string" &&
        Number.isFinite(edge.ts) &&
        Number.isFinite(edge.amount),
    )
  )
    throw new Error("Invalid observed evidence contract");
  return { ...row, result };
}

export function jsonValue(value) {
  return typeof value === "string" ? JSON.parse(value) : value;
}
export function shortId(value) {
  return value ? `${value.slice(0, 8)}…${value.slice(-4)}` : "Not recorded";
}
export function dateTime(value) {
  return value == null
    ? "Not recorded"
    : new Date(Number(value) * 1000).toLocaleString();
}
export function number(value, digits = 4) {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(digits)
    : "Unavailable";
}
