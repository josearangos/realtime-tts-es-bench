// Display helpers. They never recompute a metric: digits sent by the backend are kept.

export const NOT_AVAILABLE = "not available";

const NOTES = {
  chunk: "Audio arrives in small chunks; TTFA is the time to the first chunk.",
  sentence: "Audio arrives one sentence at a time; TTFA is the time to the first finished sentence.",
  none: "The whole audio is produced at once, so there is no time to first audio.",
};

export const granularityNote = (g) => NOTES[g] ?? "Streaming granularity is unknown.";

const isNA = (v) => v === undefined || v === null || v === NOT_AVAILABLE;
const num = (v, unit) => `${String(v)} ${unit}`;

export const fmtMs = (v) => (isNA(v) ? NOT_AVAILABLE : num(v, "ms"));
export const fmtSeconds = (v) => (isNA(v) ? NOT_AVAILABLE : num(v, "s"));
export const fmtRtf = (v) => (isNA(v) ? NOT_AVAILABLE : String(v));

// Returns {text, explanation}: explanation is non-empty only when TTFA is not available.
export function fmtTtfa(value, granularity) {
  if (!isNA(value)) return { text: fmtMs(value), explanation: "" };
  const explanation = granularity === "none"
    ? "This engine produces the whole audio at once, so there is no time to first audio."
    : "The backend did not report a time to first audio for this request.";
  return { text: NOT_AVAILABLE, explanation };
}
