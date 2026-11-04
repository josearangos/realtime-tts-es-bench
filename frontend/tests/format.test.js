import test from "node:test";
import assert from "node:assert/strict";
import { fmtMs, fmtSeconds, fmtRtf, fmtTtfa, granularityNote, NOT_AVAILABLE } from "../src/format.js";

test("numbers display with at most two decimals", () => {
  assert.equal(fmtMs(132.447083), "132.45 ms");
  assert.equal(fmtSeconds(30.812879818594105), "30.81 s");
  assert.equal(fmtRtf(0.03382912188464), "0.03");
  assert.equal(fmtMs(0.000625), "0 ms");
  assert.equal(fmtMs(123.456), "123.46 ms");
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
