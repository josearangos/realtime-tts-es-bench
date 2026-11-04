import test from "node:test";
import assert from "node:assert/strict";
import { engineOptionModel, limitModel, busyModel, panelModel } from "../src/view-model.js";
import { EnginePanel } from "../src/session.js";

const engine = (o = {}) => ({
  name: "fake", engine_version: "1", model_id: "m", license_code: "MIT", license_model: "MIT", license_flags: [],
  supports_cloning: true, streaming: { granularity: "chunk" }, input_limit_chars: 100,
  voices: [{ name: "v", kind: "stored_voice_file", cloned: true, accent_label: "es-CO", path: "/x", sha256: "abc" }],
  availability: { status: "available" }, ...o,
});

test("engine option: voices keep only the four public fields", () => {
  const m = engineOptionModel(engine());
  assert.deepEqual(Object.keys(m.voices[0]).sort(), ["accent_label", "cloned", "kind", "name"]);
  assert.equal(m.cloningBadge, "cloning");
  assert.equal(m.disabled, false);
});

test("unavailable engine is disabled with reason and hint", () => {
  const m = engineOptionModel(engine({ availability: { status: "unavailable", reason: "not_installed", hint: "pip install x" } }));
  assert.equal(m.disabled, true); assert.equal(m.reason, "not_installed"); assert.equal(m.hint, "pip install x");
});

test("restrictive license produces a warning", () => {
  const m = engineOptionModel(engine({ license_flags: ["non-commercial"] }));
  assert.ok(m.license.restrictive); assert.match(m.license.text, /Non-commercial/);
});

test("limit: smallest wins and is named; Play disabled above it", () => {
  const sel = [engine({ name: "a", input_limit_chars: 500 }), engine({ name: "b", input_limit_chars: 50 })];
  const ok = limitModel(sel, 50);
  assert.equal(ok.limit, 50); assert.equal(ok.limitedBy, "b"); assert.equal(ok.playDisabled, false);
  const over = limitModel(sel, 60);
  assert.equal(over.playDisabled, true); assert.equal(over.counter, "60 / 50");
});

test("busy model", () => {
  assert.deepEqual(busyModel({ error: "engine_busy", queue_depth: 3, message: "m" }), { queueDepth: 3, canRetry: true, message: "m" });
  assert.equal(busyModel({ error: "other" }), null);
});

test("panel model copies summary values verbatim", () => {
  const p = new EnginePanel({ engine: "fake", voice: "v" });
  p.state = "done";
  p.start = { voice: "v", accent_label: "es-CO", engine_version: "1.2", model_id: "m", granularity: "chunk" };
  p.summary = { ttfa_ms: 123.4, generation_ms: 900.25, audio_seconds: 2.5, rtf: 0.36, queue_wait_ms: 0, granularity: "chunk", kind: "interactive", load_ms: 800, first_request_after_load: true };
  const m = panelModel(p, engine());
  assert.equal(m.metrics.ttfa, "123.4 ms"); assert.equal(m.metrics.totalTime, "900.25 ms");
  assert.equal(m.metrics.audioDuration, "2.5 s"); assert.equal(m.metrics.rtf, "0.36");
  assert.equal(m.metrics.loadTime, "800 ms"); assert.ok(m.metrics.includesLoad);
  assert.equal(m.metrics.kind, "interactive"); assert.match(m.metrics.note, /not benchmark/);
  assert.equal(m.header.accent, "es-CO");
});

test("panel model: ttfa not available with granularity none", () => {
  const p = new EnginePanel({ engine: "fake", voice: "v" });
  p.start = { granularity: "none", streaming_available: false, notice: "n" };
  p.summary = { ttfa_ms: "not available", generation_ms: 5, audio_seconds: 1, rtf: 0.005, granularity: "none", kind: "interactive", queue_wait_ms: 1 };
  const m = panelModel(p);
  assert.equal(m.metrics.ttfa, "not available"); assert.match(m.metrics.ttfaExplanation, /whole audio at once/);
  assert.equal(m.metrics.granularity, "none"); assert.equal(m.notice, "n");
});

test("heard-after is labelled browser-side", () => {
  const p = new EnginePanel({ engine: "fake", voice: "v" });
  p.browser.sent_at = 10; p.browser.first_audio_scheduled_at = 60;
  assert.match(panelModel(p).heardAfter.label, /browser-side/);
});

test("comparison ranks lower-is-better, picks fastest start among real-time engines", async () => {
  const { comparisonModel } = await import("../src/view-model.js");
  const mk = (engine, ttfa, total, rtf) => { const p = new EnginePanel({ engine, voice: "v" }); p.state = "done"; p.summary = { ttfa_ms: ttfa, generation_ms: total, rtf }; return p; };
  const m = comparisonModel([mk("a", 300, 900, 0.3), mk("b", 100, 5000, 1.4), mk("c", 200, 700, 0.1)]);
  const ttfa = m.charts.find((c) => c.id === "ttfa");
  assert.deepEqual(ttfa.bars.map((b) => b.engine), ["b", "c", "a"]);
  assert.ok(ttfa.bars[0].best && !ttfa.bars[1].best);
  assert.equal(m.verdict.engine, "c"); // b starts first but is slower than real time
  assert.equal(comparisonModel([mk("a", 1, 1, 0.1)]), null);
});
