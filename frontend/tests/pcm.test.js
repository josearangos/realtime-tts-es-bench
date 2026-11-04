import test from "node:test";
import assert from "node:assert/strict";
import { s16leToFloat32, durationSeconds, assertSupportedFormat, UnsupportedFormat } from "../src/pcm.js";

const bytes = (...v) => { const b = new ArrayBuffer(v.length * 2); const d = new DataView(b); v.forEach((x, i) => d.setInt16(i * 2, x, true)); return b; };

test("known sample values convert exactly", () => {
  const f = s16leToFloat32(bytes(0, 32767, -32768));
  assert.equal(f[0], 0);
  assert.equal(f[1], 32767 / 32768);
  assert.equal(f[2], -1);
  assert.ok(f.every((x) => x >= -1 && x < 1));
});

test("little endian byte order", () => {
  const b = new Uint8Array([0x00, 0x40]).buffer; // 0x4000 = 16384
  assert.equal(s16leToFloat32(b)[0], 0.5);
});

test("odd byte length is rejected", () => {
  assert.throws(() => s16leToFloat32(new ArrayBuffer(3)), UnsupportedFormat);
});

test("non-s16le and stereo are rejected", () => {
  assert.throws(() => assertSupportedFormat({ sample_format: "f32le", channels: 1 }), UnsupportedFormat);
  assert.throws(() => assertSupportedFormat({ sample_format: "s16le", channels: 2 }), UnsupportedFormat);
  assert.doesNotThrow(() => assertSupportedFormat({ sample_format: "s16le", channels: 1 }));
});

test("duration", () => assert.equal(durationSeconds(24000, 24000), 1));

test("wavBlob writes a mono 16-bit WAV header and the samples", async () => {
  const { wavBlob } = await import("../src/pcm.js");
  const blob = wavBlob([Int16Array.of(1, -2), Int16Array.of(3)], 24000);
  const v = new DataView(await blob.arrayBuffer());
  assert.equal(blob.size, 44 + 6);
  assert.equal(String.fromCharCode(v.getUint8(0), v.getUint8(1), v.getUint8(2), v.getUint8(3)), "RIFF");
  assert.equal(v.getUint32(24, true), 24000); assert.equal(v.getUint32(40, true), 6);
  assert.deepEqual([v.getInt16(44, true), v.getInt16(46, true), v.getInt16(48, true)], [1, -2, 3]);
});
