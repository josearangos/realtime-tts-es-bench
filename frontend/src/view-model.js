// Pure view model: decides WHAT is shown. view.js only maps it to the DOM.
import { licenseWarning } from "./license.js";
import { fmtMs, fmtSeconds, fmtRtf, fmtTtfa, granularityNote, round2, METRIC_HELP } from "./format.js";

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
      help: METRIC_HELP,
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
    canDownload: panel.state === "done" && panel.chunks.length > 0,
    sampleRate: start.sample_rate ?? 24000,
  };
}

// Comparison across finished panels: ranked bars per metric (lower is better) and one speed-based pick.
// Pure: bars are scaled from the backend's raw numbers; labels are rounded for display only.
const finite = (v) => (typeof v === "number" && Number.isFinite(v) ? v : null);

const COMPARE_METRICS = [
  { id: "ttfa", title: "Time to first audio", unit: "ms", field: "ttfa", help: METRIC_HELP.ttfa, reference: null },
  { id: "rtf", title: "Real-time factor", unit: "", field: "rtf", help: METRIC_HELP.rtf, reference: { value: 1, label: "1 = real time" } },
  { id: "total", title: "Total time", unit: "ms", field: "total", help: METRIC_HELP.total, reference: null },
];

export function comparisonModel(panels) {
  const rows = panels.filter((p) => p.state === "done" && p.summary).map((p) => ({
    engine: p.engine, voice: p.start?.voice ?? p.voice ?? "",
    ttfa: finite(p.summary.ttfa_ms), total: finite(p.summary.generation_ms), rtf: finite(p.summary.rtf),
  }));
  if (rows.length < 2) return null;
  const charts = [];
  for (const m of COMPARE_METRICS) {
    const items = rows.filter((r) => r[m.field] !== null).sort((a, b) => a[m.field] - b[m.field]);
    if (items.length < 2) continue;
    const max = Math.max(...items.map((r) => r[m.field]), m.reference?.value ?? 0) || 1;
    charts.push({
      id: m.id, title: m.title, unit: m.unit, help: m.help,
      reference: m.reference ? { label: m.reference.label, pct: (m.reference.value / max) * 100 } : null,
      bars: items.map((r, i) => ({ engine: r.engine, voice: r.voice, text: round2(r[m.field]), pct: Math.max((r[m.field] / max) * 100, 1), best: i === 0 })),
    });
  }
  // Pick: among engines that outrun real time, the one that starts speaking first.
  const smooth = rows.filter((r) => r.rtf !== null && r.rtf < 1 && r.ttfa !== null);
  const pool = smooth.length ? smooth : rows.filter((r) => r.ttfa !== null);
  let verdict = null;
  if (pool.length) {
    const w = pool.reduce((a, b) => (b.ttfa < a.ttfa ? b : a));
    const speed = w.rtf !== null && w.rtf > 0 ? ` and generates ${round2(1 / w.rtf)}× faster than real time` : "";
    verdict = {
      engine: w.engine, voice: w.voice,
      reason: smooth.length
        ? `Starts speaking after ${round2(w.ttfa)} ms${speed}.`
        : `Starts earliest (${round2(w.ttfa)} ms), but no engine generated faster than real time, so live playback may stutter.`,
      rule: "Pick = earliest first audio among engines that generate faster than real time. It measures speed only.",
    };
  }
  return { charts, verdict, listenNote: "Speed is not quality. Use Replay on each result to judge naturalness and pronunciation before choosing." };
}
