// Thin DOM mapping of the view model. All decisions live in view-model.js. Text is set with textContent only.

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v === null || v === undefined) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) el.append(c.nodeType ? c : document.createTextNode(String(c)));
  return el;
}

const clear = (el) => { el.replaceChildren(); return el; };

export function renderBanner(el, message) {
  clear(el);
  if (!message) return;
  el.append(h("div", { class: "banner error", role: "alert" }, message.text, message.command ? h("code", {}, message.command) : null));
}

export function licenseLine(license) {
  return h("div", { class: "license" },
    h("span", {}, `License: ${license.code ?? "unknown"} (${license.model ?? "unknown"})`),
    license.restrictive ? h("div", { class: "banner warning", role: "alert" }, "⚠ ", license.text) : null);
}

export function renderEngines(el, { models, selected, onToggle, onVoice }) {
  clear(el);
  for (const m of models) {
    const checked = selected.has(m.name);
    const voiceSelect = h("select", { "aria-label": `Voice for ${m.name}`, disabled: m.disabled || !checked, onchange: (e) => onVoice(m.name, e.target.value) },
      m.voices.map((v) => h("option", { value: v.name, selected: selected.get(m.name) === v.name },
        `${v.name}${v.accent_label ? ` — ${v.accent_label}` : ""}`)));
    el.append(h("div", { class: `engine${m.disabled ? " disabled" : ""}` },
      h("label", {}, h("input", { type: "checkbox", checked, disabled: m.disabled, onchange: (e) => onToggle(m.name, e.target.checked) }),
        h("strong", {}, ` ${m.name}`), m.cloningBadge ? h("span", { class: "badge" }, m.cloningBadge) : null,
        h("span", { class: "meta" }, ` ${m.engineVersion} · ${m.modelId} · limit ${m.inputLimit} chars · ${m.granularity ?? "?"}`)),
      m.disabled ? h("div", { class: "unavailable" }, `Unavailable: ${m.reason}. ${m.hint}`) : voiceSelect,
      licenseLine(m.license)));
  }
}

export function renderCorpus(el, { entries, onPick }) {
  clear(el);
  for (const s of entries.slice(0, 200)) {
    el.append(h("li", {}, h("button", { type: "button", class: "link", onclick: () => onPick(s) }, `${s.id}`), " ", s.text));
  }
  if (entries.length === 0) el.append(h("li", { class: "empty" }, "No sentences match."));
}

function metricRow(label, value, extra) {
  return h("div", { class: "metric" }, h("dt", {}, label), h("dd", {}, value, extra ? h("small", {}, ` ${extra}`) : null));
}

export function renderPanels(el, { models, onReplay, onRetry, onEnableAudio }) {
  clear(el);
  for (const { model: m, index } of models) {
    const head = m.header;
    const box = h("section", { class: `panel state-${m.state}` },
      h("header", {},
        h("h3", {}, head.engine, " ", h("span", { class: "state" }, m.state)),
        h("div", { class: "meta" }, [head.voice, head.accent, head.engineVersion, head.modelId].filter(Boolean).join(" · ")),
        head.license ? licenseLine(head.license) : null));
    if (m.notice) box.append(h("div", { class: "notice" }, m.notice));
    if (m.audioBlocked) box.append(h("button", { type: "button", onclick: onEnableAudio }, "Enable audio"));
    if (m.error) {
      const e = m.error;
      box.append(h("div", { class: "banner error", role: "alert" }, e.message,
        e.available ? h("div", {}, `Available: ${e.available.join(", ")}`) : null,
        e.busy ? h("div", {}, `Queue depth: ${e.busy.queueDepth ?? "?"} `, h("button", { type: "button", onclick: () => onRetry(index) }, "Retry")) : null));
    }
    if (m.metrics) {
      const x = m.metrics;
      box.append(h("dl", { class: "metrics" },
        metricRow("Time to first audio", x.ttfa, x.granularity ? `(${x.granularity})` : ""),
        x.ttfaExplanation ? h("p", { class: "explain" }, x.ttfaExplanation) : null,
        h("p", { class: "explain" }, x.granularityNote),
        metricRow("Total time", x.totalTime),
        metricRow("Audio duration", x.audioDuration),
        metricRow("Real-time factor", x.rtf),
        x.queueWait !== null ? metricRow("Queue wait", x.queueWait) : null,
        x.loadTime !== null ? metricRow("Model load", x.loadTime, x.includesLoad ? "includes model load" : "") : null),
        h("p", { class: "explain" }, `${x.kind}: ${x.note}`));
    }
    if (m.heardAfter) box.append(h("p", { class: "explain" }, `Heard after: ${m.heardAfter.text} (${m.heardAfter.label})`));
    if (m.underruns) box.append(h("p", { class: "explain" }, `Playback underruns: ${m.underruns}`));
    if (m.canReplay) box.append(h("button", { type: "button", onclick: () => onReplay(index) }, "Replay"));
    el.append(box);
  }
}
