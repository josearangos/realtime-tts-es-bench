// Typed REST client for the 007 backend (+ corpus).

export const START_COMMAND = "python -m tts_bench.backend serve";

export class BackendUnreachable extends Error {
  constructor(url) {
    super(`Backend not reachable at ${url}. Start it with: ${START_COMMAND}`);
    this.name = "BackendUnreachable";
    this.url = url;
    this.startCommand = START_COMMAND;
  }
}

export class BackendError extends Error {
  constructor(body, status) {
    super(body.message || body.error || "Backend error");
    this.name = "BackendError";
    this.error = body.error;
    this.available = body.available;
    this.status = status;
    this.body = body;
  }
}

const trim = (u) => u.replace(/\/+$/, "");

async function request(baseUrl, path, init, fetchImpl = globalThis.fetch) {
  const url = trim(baseUrl) + path;
  let res;
  try {
    res = await fetchImpl(url, init);
  } catch {
    throw new BackendUnreachable(trim(baseUrl));
  }
  let body;
  try {
    body = await res.json();
  } catch {
    throw new BackendUnreachable(trim(baseUrl));
  }
  if (!res.ok) {
    if (body && typeof body === "object" && body.error) throw new BackendError(body, res.status);
    throw new BackendUnreachable(trim(baseUrl));
  }
  return body;
}

export const getHealth = (baseUrl, f) => request(baseUrl, "/v1/health", undefined, f);
export const getEngines = (baseUrl, f) => request(baseUrl, "/v1/engines", undefined, f);
export const refreshEngines = (baseUrl, f) => request(baseUrl, "/v1/engines/refresh", { method: "POST" }, f);
export const getCorpus = (baseUrl, f) => request(baseUrl, "/v1/corpus", undefined, f);
