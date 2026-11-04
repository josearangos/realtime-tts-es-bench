// End-to-end check against the real gateway with the fake engine (SC-001, SC-002). No weights, no browser.
import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
import { openSynthesis } from "../src/stream.js";
import { getEngines } from "../src/api.js";
import { engineOptionModel, panelModel } from "../src/view-model.js";
import { EnginePanel } from "../src/session.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const python = process.env.TTS_PYTHON ?? path.join(root, ".venv-core/bin/python");

const freePort = () => new Promise((res) => { const s = net.createServer().listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); }); });

async function withGateway(env, fn) {
  const port = await freePort();
  const proc = spawn(python, [path.join(root, "frontend/tests/serve_fake.py"), String(port)], { cwd: root, env: { ...process.env, ...env }, stdio: ["ignore", "inherit", "inherit"] });
  const base = `http://127.0.0.1:${port}`;
  try {
    for (let i = 0; ; i++) {
      try { const r = await fetch(`${base}/v1/health`); if (r.ok) break; } catch { /* not yet */ }
      if (i > 100) throw new Error("gateway did not start");
      await new Promise((r) => setTimeout(r, 100));
    }
    return await fn(base);
  } finally { proc.kill(); }
}

function synth(base, request) {
  return new Promise((resolve, reject) => {
    const t0 = performance.now();
    const rec = { start: null, chunks: [], summary: null, firstChunkAt: null, summaryAt: null, error: null };
    openSynthesis(base, request, {
      onStart: (m) => { rec.start = m; },
      onChunk: (meta, pcm) => { rec.firstChunkAt ??= performance.now() - t0; rec.chunks.push({ meta, pcm }); },
      onSummary: (m) => { rec.summary = m; rec.summaryAt = performance.now() - t0; },
      onError: (e) => { rec.error = e; },
      onClose: () => (rec.error ? reject(new Error(JSON.stringify(rec.error))) : resolve(rec)),
    });
  });
}

const firstVoice = (engines, name) => engines.find((e) => e.name === name).voices[0].name;

// Run 1: chunked fake engine with known delays.
await withGateway({ TTS_FAKE_FIRST_CHUNK_S: "0.1", TTS_FAKE_CHUNK_INTERVAL_S: "0.15", TTS_FAKE_CHUNKS: "5", TTS_FAKE_AUDIO_S: "1.0" }, async (base) => {
  const { engines } = await getEngines(base);
  const rec = await synth(base, { engine: "fake", voice: firstVoice(engines, "fake"), text: "Buenos días, ¿en qué le puedo ayudar?" });
  assert.ok(rec.chunks.length >= 2, "expected several chunks");
  assert.ok(rec.firstChunkAt < rec.summaryAt, "first chunk must arrive before the summary (SC-001)");
  console.log(`first chunk before summary by ${(rec.summaryAt - rec.firstChunkAt).toFixed(0)} ms (first chunk at ${rec.firstChunkAt.toFixed(0)} ms, summary at ${rec.summaryAt.toFixed(0)} ms)`);

  // SC-002: displayed values equal the summary exactly.
  const panel = new EnginePanel({ engine: "fake", voice: rec.start.voice });
  panel.start = rec.start; panel.summary = rec.summary; panel.state = "done";
  const m = panelModel(panel, engines.find((e) => e.name === "fake")).metrics;
  const s = rec.summary;
  assert.equal(m.ttfa, `${s.ttfa_ms} ms`);
  assert.equal(m.totalTime, `${s.generation_ms} ms`);
  assert.equal(m.audioDuration, `${s.audio_seconds} s`);
  assert.equal(m.rtf, String(s.rtf));
  assert.equal(m.kind, "interactive");
  const model = engineOptionModel(engines.find((e) => e.name === "fake"));
  assert.ok(model.voices.every((v) => Object.keys(v).length === 4));
  console.log("displayed values equal the summary: ok");
});

// Run 2 (US2): a non-streaming engine reports TTFA as not available.
await withGateway({ TTS_FAKE_GRANULARITY: "none", TTS_FAKE_CHUNKS: "1" }, async (base) => {
  const { engines } = await getEngines(base);
  const rec = await synth(base, { engine: "fake", voice: firstVoice(engines, "fake"), text: "Hola." });
  const panel = new EnginePanel({ engine: "fake", voice: rec.start.voice });
  panel.start = rec.start; panel.summary = rec.summary; panel.state = "done";
  const m = panelModel(panel).metrics;
  assert.equal(rec.summary.ttfa_ms, "not available");
  assert.equal(m.ttfa, "not available");
  assert.match(m.ttfaExplanation, /whole audio at once/);
  assert.equal(m.granularity, "none");
  console.log("granularity none: TTFA renders as not available with explanation: ok");
});

console.log("e2e passed");
