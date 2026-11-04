import test, { beforeEach } from "node:test";
import assert from "node:assert/strict";
import { FakeWebSocket } from "./fake-ws.js";
import { openSynthesis, wsUrl } from "../src/stream.js";

const START = { type: "start", sample_rate: 24000, channels: 1, sample_format: "s16le", granularity: "chunk" };
const rec = () => {
  const log = [];
  return { log, handlers: {
    onStart: (m) => log.push(["start", m]), onChunk: (m, p) => log.push(["chunk", m, p]),
    onSummary: (m) => log.push(["summary", m]), onError: (m) => log.push(["error", m]), onClose: () => log.push(["close"]),
  } };
};
const names = (log) => log.map((e) => e[0]);
beforeEach(() => FakeWebSocket.reset());

test("url conversion", () => assert.equal(wsUrl("http://127.0.0.1:8000/"), "ws://127.0.0.1:8000/v1/ws/synthesize"));

test("happy path order and request is sent once on open", () => {
  const { log, handlers } = rec();
  openSynthesis("http://h", { engine: "fake", text: "hola" }, handlers, FakeWebSocket);
  const ws = FakeWebSocket.instances[0];
  assert.equal(ws.binaryType, "arraybuffer");
  ws.open();
  assert.deepEqual(ws.sentJson, [{ engine: "fake", text: "hola" }]);
  ws.serverText(START);
  ws.serverText({ type: "chunk", index: 0, at_ms: 5, gap_ms: 0, samples: 2 });
  ws.serverBinary(new Int16Array([1, -2]));
  ws.serverText({ type: "summary", ttfa_ms: 5 });
  ws.serverClose();
  assert.deepEqual(names(log), ["start", "chunk", "summary", "close"]);
});

test("chunk metadata pairs with the next binary frame", () => {
  const { log, handlers } = rec();
  openSynthesis("http://h", {}, handlers, FakeWebSocket);
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText(START);
  ws.serverText({ type: "chunk", index: 0, samples: 1 }); ws.serverBinary(new Int16Array([7]));
  ws.serverText({ type: "chunk", index: 1, samples: 1 }); ws.serverBinary(new Int16Array([9]));
  const chunks = log.filter((e) => e[0] === "chunk");
  assert.deepEqual(chunks.map((c) => [c[1].index, Array.from(c[2])]), [[0, [7]], [1, [9]]]);
});

test("error message before audio, no unreachable report", () => {
  const { log, handlers } = rec();
  openSynthesis("http://h", {}, handlers, FakeWebSocket);
  const ws = FakeWebSocket.instances[0];
  ws.open();
  ws.serverText({ type: "error", error: "unknown_voice", message: "nope", available: ["a"] });
  ws.serverClose();
  const errs = log.filter((e) => e[0] === "error");
  assert.equal(errs.length, 1);
  assert.deepEqual(errs[0][1], { error: "unknown_voice", message: "nope", available: ["a"] });
});

test("close before start without error is backend_unreachable", () => {
  const { log, handlers } = rec();
  openSynthesis("http://h", {}, handlers, FakeWebSocket);
  FakeWebSocket.instances[0].failToOpen();
  assert.equal(log.find((e) => e[0] === "error")[1].error, "backend_unreachable");
  assert.match(log.find((e) => e[0] === "error")[1].message, /python -m tts_bench.backend serve/);
});

test("close after start without summary is connection_lost", () => {
  const { log, handlers } = rec();
  openSynthesis("http://h", {}, handlers, FakeWebSocket);
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText(START); ws.serverClose();
  assert.equal(log.find((e) => e[0] === "error")[1].error, "connection_lost");
});

test("cancel sends the cancel message, closes, and reports no error", () => {
  const { log, handlers } = rec();
  const h = openSynthesis("http://h", {}, handlers, FakeWebSocket);
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText(START);
  h.cancel();
  assert.deepEqual(ws.sentJson.at(-1), { cancel: true });
  assert.ok(ws.closedByClient);
  assert.deepEqual(names(log), ["start", "close"]);
});

test("unpaired binary frame is a protocol error and closes", () => {
  const { log, handlers } = rec();
  openSynthesis("http://h", {}, handlers, FakeWebSocket);
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText(START); ws.serverBinary(new Int16Array([1]));
  assert.equal(log.find((e) => e[0] === "error")[1].error, "protocol_error");
  assert.ok(ws.closedByClient);
});

test("unsupported format is reported, not played", () => {
  const { log, handlers } = rec();
  openSynthesis("http://h", {}, handlers, FakeWebSocket);
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText({ ...START, channels: 2 });
  assert.equal(log.find((e) => e[0] === "error")[1].error, "unsupported_format");
  assert.ok(!names(log).includes("start"));
});
