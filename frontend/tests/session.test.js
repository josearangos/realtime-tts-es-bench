import test, { beforeEach } from "node:test";
import assert from "node:assert/strict";
import { FakeWebSocket } from "./fake-ws.js";
import { runPanel, ComparisonSession, EnginePanel } from "../src/session.js";

const START = { type: "start", sample_rate: 24000, channels: 1, sample_format: "s16le", granularity: "chunk", voice: "v", accent_label: "es" };
const SUMMARY = { type: "summary", ttfa_ms: 10, generation_ms: 50, audio_seconds: 1, rtf: 0.05, granularity: "chunk", kind: "interactive", queue_wait_ms: 0 };

class FakePlayer {
  constructor() { this.calls = []; this.underruns = 0; this.state = "running"; this.onEnded = null; this.pushed = 0; }
  start(rate) { this.calls.push(["start", rate]); }
  push() { this.pushed++; this.calls.push(["push"]); }
  finish() { this.calls.push(["finish"]); }
  stop() { this.calls.push(["stop"]); }
  end() { this.onEnded?.(); }
}
let players;
const deps = (extra = {}) => ({
  baseUrl: "http://h", WebSocketImpl: FakeWebSocket, createPlayer: () => { const p = new FakePlayer(); players.push(p); return p; },
  now: (() => { let t = 0; return () => (t += 10); })(), ...extra,
});
const tick = () => new Promise((r) => setImmediate(r));
const chunk = (ws, i = 0) => { ws.serverText({ type: "chunk", index: i, at_ms: 1, gap_ms: 0, samples: 2 }); ws.serverBinary(new Int16Array([1, 2])); };
beforeEach(() => { FakeWebSocket.reset(); players = []; });

test("single panel: connecting -> streaming -> playing -> done; playback starts before summary", async () => {
  const states = [];
  const panel = new EnginePanel({ engine: "fake", voice: "v" });
  const run = runPanel(panel, "hola", deps({ notify: (p) => p && states.push(p.state) }));
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText(START);
  assert.equal(panel.state, "streaming");
  chunk(ws);
  assert.equal(panel.state, "playing");
  assert.deepEqual(players[0].calls.slice(0, 2), [["start", 24000], ["push"]]);
  assert.equal(panel.summary, null); // summary not yet received
  ws.serverText(SUMMARY); ws.serverClose();
  assert.equal(panel.state, "playing"); // still playing
  players[0].end();
  await run.promise;
  assert.equal(panel.state, "done");
  assert.deepEqual([...new Set(states)], ["connecting", "streaming", "playing", "done"]);
  assert.deepEqual(panel.summary, { ...SUMMARY });
  assert.ok(panel.heardAfterMs > 0);
});

test("Stop sends cancel and the panel becomes cancelled", async () => {
  const panel = new EnginePanel({ engine: "fake", voice: "v" });
  const run = runPanel(panel, "hola", deps());
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText(START); chunk(ws);
  run.stop();
  await run.promise;
  assert.equal(panel.state, "cancelled");
  assert.deepEqual(ws.sentJson.at(-1), { cancel: true });
  assert.ok(players[0].calls.some((c) => c[0] === "stop"));
});

test("backend error fails the panel and keeps message and available list", async () => {
  const panel = new EnginePanel({ engine: "fake", voice: "x" });
  const run = runPanel(panel, "hola", deps());
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText({ type: "error", error: "unknown_voice", message: "no", available: ["a", "b"] }); ws.serverClose();
  await run.promise;
  assert.equal(panel.state, "failed");
  assert.equal(panel.error.message, "no"); assert.deepEqual(panel.error.available, ["a", "b"]);
});

test("backend_unreachable is reported distinctly", async () => {
  const panel = new EnginePanel({ engine: "fake", voice: "v" });
  const run = runPanel(panel, "hola", deps());
  FakeWebSocket.instances[0].failToOpen();
  await run.promise;
  assert.equal(panel.state, "failed"); assert.equal(panel.error.error, "backend_unreachable");
});

test("suspended audio context sets audio_blocked and keeps chunks", () => {
  const panel = new EnginePanel({ engine: "fake", voice: "v" });
  runPanel(panel, "hola", deps({ createPlayer: () => { const p = new FakePlayer(); p.state = "suspended"; players.push(p); return p; } }));
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText(START); chunk(ws);
  assert.ok(panel.audio_blocked); assert.equal(panel.chunks.length, 1);
});

// ---- comparison ----
const selections = [{ engine: "a", voice: "v" }, { engine: "b", voice: "v" }, { engine: "c", voice: "v" }];
const finishPanel = async (i) => {
  const ws = FakeWebSocket.instances[i];
  ws.open(); ws.serverText(START); chunk(ws); ws.serverText(SUMMARY); ws.serverClose();
  await tick();
};

test("comparison: next panel waits for done and for playback to end", async () => {
  const s = new ComparisonSession({ text: "hola", selections, deps: deps() });
  const running = s.run();
  await tick();
  assert.equal(FakeWebSocket.instances.length, 1);
  assert.deepEqual(s.panels.map((p) => p.state), ["connecting", "waiting", "waiting"]);
  await finishPanel(0);
  assert.equal(FakeWebSocket.instances.length, 1); // playback has not ended yet
  players[0].end(); await tick();
  assert.equal(FakeWebSocket.instances.length, 2);
  await finishPanel(1); players[1].end(); await tick();
  await finishPanel(2); players[2].end();
  await running;
  assert.equal(s.state, "finished");
  assert.deepEqual(s.panels.map((p) => p.state), ["done", "done", "done"]);
  const texts = FakeWebSocket.instances.map((w) => w.sentJson[0].text);
  assert.deepEqual(texts, ["hola", "hola", "hola"]);
});

test("comparison: a failed panel does not stop later panels", async () => {
  const s = new ComparisonSession({ text: "hola", selections: selections.slice(0, 2), deps: deps() });
  const running = s.run(); await tick();
  const ws = FakeWebSocket.instances[0];
  ws.open(); ws.serverText({ type: "error", error: "synthesis_failed", message: "boom" }); ws.serverClose();
  await tick();
  assert.equal(s.panels[0].state, "failed");
  assert.equal(FakeWebSocket.instances.length, 2);
  await finishPanel(1); players[0].end();
  await running;
  assert.equal(s.panels[1].state, "done");
});

test("comparison: Stop during panel 2 cancels it, panel 3 not_run, panel 1 audio kept", async () => {
  const s = new ComparisonSession({ text: "hola", selections, deps: deps() });
  const running = s.run(); await tick();
  await finishPanel(0); players[0].end(); await tick();
  const ws2 = FakeWebSocket.instances[1];
  ws2.open(); ws2.serverText(START); chunk(ws2);
  s.stop();
  await running;
  assert.deepEqual(s.panels.map((p) => p.state), ["done", "cancelled", "not_run"]);
  assert.equal(s.panels[0].chunks.length, 1);
  assert.equal(FakeWebSocket.instances.length, 2);
  assert.equal(s.state, "stopped");
});

test("replay plays stored chunks and sends no new message", async () => {
  const s = new ComparisonSession({ text: "hola", selections: selections.slice(0, 1), deps: deps() });
  const running = s.run(); await tick();
  await finishPanel(0); players[0].end(); await running;
  const sentBefore = FakeWebSocket.instances.map((w) => w.sent.length);
  const replay = s.replay(s.panels[0]);
  assert.equal(s.panels[0].state, "playing");
  assert.equal(players[1].pushed, 1);
  players[1].end(); await replay;
  assert.equal(s.panels[0].state, "done");
  assert.deepEqual(FakeWebSocket.instances.map((w) => w.sent.length), sentBefore);
  assert.equal(FakeWebSocket.instances.length, 1);
});
