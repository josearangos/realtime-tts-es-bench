// Display helpers. They never recompute a metric: values are only rounded for display (at most two decimals).

export const NOT_AVAILABLE = "not available";

const NOTES = {
  chunk: "Audio arrives in small chunks; TTFA is the time to the first chunk.",
  sentence: "Audio arrives one sentence at a time; TTFA is the time to the first finished sentence.",
  none: "The whole audio is produced at once, so there is no time to first audio.",
};

export const granularityNote = (g) => NOTES[g] ?? "Streaming granularity is unknown.";

const isNA = (v) => v === undefined || v === null || v === NOT_AVAILABLE;
// At most two decimals; trailing zeros dropped. Non-numeric values are shown as sent.
export const round2 = (v) => (Number.isFinite(Number(v)) && v !== "" && typeof v !== "boolean" ? String(Math.round((Number(v) + Number.EPSILON) * 100) / 100) : String(v));
const num = (v, unit) => `${round2(v)} ${unit}`;

export const fmtMs = (v) => (isNA(v) ? NOT_AVAILABLE : num(v, "ms"));
export const fmtSeconds = (v) => (isNA(v) ? NOT_AVAILABLE : num(v, "s"));
export const fmtRtf = (v) => (isNA(v) ? NOT_AVAILABLE : round2(v));

// Returns {text, explanation}: explanation is non-empty only when TTFA is not available.
export function fmtTtfa(value, granularity) {
  if (!isNA(value)) return { text: fmtMs(value), explanation: "" };
  const explanation = granularity === "none"
    ? "This engine produces the whole audio at once, so there is no time to first audio."
    : "The backend did not report a time to first audio for this request.";
  return { text: NOT_AVAILABLE, explanation };
}

// Tooltip copy per metric: what it is and which direction is better.
export const METRIC_HELP = {
  ttfa: "Time to first audio: how long after pressing Play until the first sound is ready. Lower is better. Under about 300 ms feels instant; over 1 s the wait is noticeable.",
  total: "Total time: how long the engine took to generate all of the audio. Lower is better. Compare it with the audio duration: generating faster than the audio lasts means smooth playback.",
  duration: "Audio duration: length of the generated speech. Not good or bad on its own; for the same text it shows how fast the voice speaks.",
  rtf: "Real-time factor: generation time divided by audio duration. Lower is better. Below 1 the engine is faster than real time; above 1 it cannot keep up and live playback will stutter.",
  queue: "Queue wait: time the request waited for the engine to be free. Lower is better; 0 is ideal. A high value means another request was running.",
  load: "Model load: time spent loading the model into memory. Lower is better. It is only paid on the first request after the engine starts.",
};
