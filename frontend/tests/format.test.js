import test from "node:test";
import assert from "node:assert/strict";
import { fmtMs, fmtSeconds, fmtRtf, fmtTtfa, granularityNote, NOT_AVAILABLE } from "../src/format.js";

test("numbers display unchanged", () => {
  assert.equal(fmtMs(123.456), "123.456 ms");
  assert.equal(fmtMs(120), "120 ms");
  assert.equal(fmtSeconds(2.5), "2.5 s");
  assert.equal(fmtRtf(0.31), "0.31");
  assert.equal(fmtRtf(0.3), "0.3");
});

test("not available for the exact string and absent values", () => {
  assert.equal(fmtMs("not available"), NOT_AVAILABLE);
  assert.equal(fmtRtf(undefined), NOT_AVAILABLE);
  assert.equal(fmtRtf(null), NOT_AVAILABLE);
});

test("TTFA with granularity none is explained", () => {
  const t = fmtTtfa("not available", "none");
  assert.equal(t.text, "not available");
  assert.match(t.explanation, /whole audio at once/);
  assert.equal(fmtTtfa(42, "chunk").explanation, "");
});

test("granularity notes", () => {
  for (const g of ["chunk", "sentence", "none"]) assert.ok(granularityNote(g).length > 10);
  assert.notEqual(granularityNote("chunk"), granularityNote("sentence"));
});
