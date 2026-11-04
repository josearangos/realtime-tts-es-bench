import test from "node:test";
import assert from "node:assert/strict";
import { engineOptionModel, panelModel } from "../src/view-model.js";
import { EnginePanel } from "../src/session.js";

test("unexpected voice fields never reach the models", () => {
  const engine = {
    name: "fake", availability: { status: "available" }, license_flags: [], streaming: { granularity: "chunk" },
    voices: [{ name: "v", kind: "k", cloned: true, accent_label: "es", path: "/secret/ref.wav", sha256: "deadbeef", consent_id: "cons-1", recording_id: "rec-9" }],
  };
  const p = new EnginePanel({ engine: "fake", voice: "v" });
  p.start = { voice: "v", accent_label: "es", path: "/secret/ref.wav", sha256: "deadbeef", consent_id: "cons-1" };
  const dump = JSON.stringify([engineOptionModel(engine), panelModel(p, engine)]);
  for (const bad of ["/secret", "deadbeef", "cons-1", "rec-9", "ref.wav"]) assert.ok(!dump.includes(bad), bad);
});
