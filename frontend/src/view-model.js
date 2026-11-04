// Pure view model: decides WHAT is shown. view.js only maps it to the DOM.
import { licenseWarning } from "./license.js";
import { fmtMs, fmtSeconds, fmtRtf, fmtTtfa, granularityNote } from "./format.js";

export function engineOptionModel(engine) {
  const availability = engine.availability ?? {};
  const available = availability.status === "available";
  const license = licenseWarning(engine);
  return {
    name: engine.name,
    available,
    disabled: !available,
    reason: available ? "" : (availability.reason ?? "unavailable"),
    hint: available ? "" : (availability.hint ?? ""),
    cloningBadge: engine.supports_cloning ? "cloning" : "",
    engineVersion: engine.engine_version ?? "",
    modelId: engine.model_id ?? "",
    license: { code: license.license_code, model: license.license_model, text: license.text, restrictive: license.restrictive, flags: license.flags },
    granularity: engine.streaming?.granularity ?? null,
    inputLimit: engine.input_limit_chars ?? null,
    voices: (engine.voices ?? []).map((v) => ({ name: v.name, kind: v.kind, cloned: v.cloned, accent_label: v.accent_label })),
  };
}

// Smallest limit among selected engines wins; the engine that sets it is named.
export function limitModel(selectedEngines, textLength) {
  const limited = selectedEngines.filter((e) => typeof e.input_limit_chars === "number");
  if (limited.length === 0) return { limit: null, limitedBy: null, over: false, playDisabled: false, counter: String(textLength) };
  const setter = limited.reduce((a, b) => (b.input_limit_chars < a.input_limit_chars ? b : a));
  const over = textLength > setter.input_limit_chars;
  return {
    limit: setter.input_limit_chars, limitedBy: setter.name, over, playDisabled: over,
    counter: `${textLength} / ${setter.input_limit_chars}`,
  };
}

export function busyModel(error) {
  if (error?.error !== "engine_busy") return null;
  return { queueDepth: error.queue_depth ?? null, canRetry: true, message: error.message };
}

export function errorModel(error) {
  if (!error) return null;
  return {
    code: error.error, message: error.message,
    available: Array.isArray(error.available) ? error.available : null,
    unreachable: error.error === "backend_unreachable",
    busy: busyModel(error),
  };
}

export function panelModel(panel, engineMeta = null) {
  const start = panel.start ?? {};
  const summary = panel.summary;
  const header = {
    engine: panel.engine,
    voice: start.voice ?? panel.voice,
    accent: start.accent_label ?? null,
    engineVersion: start.engine_version ?? engineMeta?.engine_version ?? null,
    modelId: start.model_id ?? engineMeta?.model_id ?? null,
    license: engineMeta ? engineOptionModel(engineMeta).license : null,
  };
  const granularity = summary?.granularity ?? start.granularity ?? null;
  let metrics = null;
  if (summary) {
    const ttfa = fmtTtfa(summary.ttfa_ms, granularity);
    metrics = {
      kind: summary.kind,
      note: "Live figures are interactive measurements, not benchmark results.",
      ttfa: ttfa.text,
      ttfaExplanation: ttfa.explanation,
      granularity,
      granularityNote: granularityNote(granularity),
      totalTime: fmtMs(summary.generation_ms),
      audioDuration: fmtSeconds(summary.audio_seconds),
      rtf: fmtRtf(summary.rtf),
      queueWait: summary.queue_wait_ms === undefined ? null : fmtMs(summary.queue_wait_ms),
      loadTime: summary.load_ms === undefined ? null : fmtMs(summary.load_ms),
      includesLoad: summary.first_request_after_load === true,
    };
  }
  const heard = panel.heardAfterMs;
  return {
    state: panel.state,
    header,
    notice: start.streaming_available === false ? (start.notice ?? granularityNote("none")) : null,
    metrics,
    heardAfter: heard === null ? null : { text: `${Math.round(heard)} ms`, label: "browser-side, not a benchmark number" },
    underruns: panel.underruns,
    audioBlocked: panel.audio_blocked,
    error: errorModel(panel.error),
    canReplay: panel.state === "done" && panel.chunks.length > 0,
  };
}
