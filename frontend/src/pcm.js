// PCM helpers. The backend sends s16le, mono (contract assumption 2).

export class UnsupportedFormat extends Error {
  constructor(message) { super(message); this.name = "UnsupportedFormat"; }
}

export function assertSupportedFormat({ sample_format, channels }) {
  if (sample_format !== "s16le") throw new UnsupportedFormat(`Unsupported sample format '${sample_format}' (expected s16le).`);
  if (channels !== 1) throw new UnsupportedFormat(`Unsupported channel count ${channels} (expected 1).`);
}

// ArrayBuffer of little-endian 16-bit samples -> Int16Array (endianness-safe).
export function int16FromBuffer(arrayBuffer) {
  if (arrayBuffer.byteLength % 2 !== 0) throw new UnsupportedFormat("Audio frame has an odd number of bytes.");
  const view = new DataView(arrayBuffer);
  const out = new Int16Array(arrayBuffer.byteLength / 2);
  for (let i = 0; i < out.length; i++) out[i] = view.getInt16(i * 2, true);
  return out;
}

export function int16ToFloat32(int16) {
  const out = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) out[i] = int16[i] / 32768;
  return out;
}

export function s16leToFloat32(arrayBuffer) {
  return int16ToFloat32(int16FromBuffer(arrayBuffer));
}

export function durationSeconds(samples, sampleRate) {
  return samples / sampleRate;
}

// Mono 16-bit PCM WAV file from the streamed chunks (the exact samples that were played).
export function wavBlob(int16Chunks, sampleRate) {
  const samples = int16Chunks.reduce((n, c) => n + c.length, 0);
  const buf = new ArrayBuffer(44 + samples * 2);
  const v = new DataView(buf);
  const str = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
  str(0, "RIFF"); v.setUint32(4, 36 + samples * 2, true); str(8, "WAVE"); str(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sampleRate, true); v.setUint32(28, sampleRate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, samples * 2, true);
  let o = 44;
  for (const c of int16Chunks) for (let i = 0; i < c.length; i++, o += 2) v.setInt16(o, c[i], true);
  return new Blob([buf], { type: "audio/wav" });
}
