// Wiring: loads engines/corpus, handles form events, drives the session.
import { getEngines, refreshEngines, getCorpus, BackendUnreachable, BackendError } from "./api.js";
import { createPlayer } from "./player.js";
import { ComparisonSession } from "./session.js";
import { engineOptionModel, limitModel, panelModel } from "./view-model.js";
import { filterCorpus, campaigns, activate } from "./corpus.js";
import { h, renderBanner, renderEngines, renderPanels, renderCorpus } from "./view.js";

const state = {
  baseUrl: "http://127.0.0.1:8000",
  engines: [],
  selected: new Map(), // engine name -> voice name
  corpus: [],
  session: null,
  ctx: null,
  running: false,
};

const root = document.getElementById("app");
const banner = h("div", { id: "banner" });
const backendInput = h("input", { type: "text", id: "backend-url", value: state.baseUrl, "aria-label": "Backend URL", onchange: (e) => { state.baseUrl = e.target.value.trim(); load(); } });
const refreshBtn = h("button", { type: "button", onclick: () => load(true) }, "Refresh");
const enginesEl = h("div", { id: "engines" });
const textArea = h("textarea", { id: "text", rows: 4, lang: "es", placeholder: "Escriba el texto en español…", oninput: () => update() });
const counter = h("div", { id: "counter", class: "counter" });
const playBtn = h("button", { type: "button", id: "play", onclick: () => play() }, "Play");
const stopBtn = h("button", { type: "button", id: "stop", onclick: () => stop() }, "Stop");
const panelsEl = h("div", { id: "panels", class: "panels" });
const corpusFilter = h("input", { type: "search", placeholder: "Filter corpus…", "aria-label": "Filter corpus", oninput: () => renderCorpusList() });
const campaignSelect = h("select", { "aria-label": "Campaign", onchange: () => renderCorpusList() });
const corpusList = h("ul", { class: "corpus-list" });

root.append(
  h("h1", {}, "Real-time TTS tester"),
  h("p", { class: "note" }, "A live-testing aid, not a benchmark: figures shown are interactive measurements."),
  banner,
  h("div", { class: "row" }, h("label", {}, "Backend URL ", backendInput), refreshBtn),
  h("h2", {}, "Engines"), enginesEl,
  h("h2", {}, "Text"), textArea, counter,
  h("div", { class: "row" }, playBtn, stopBtn),
  panelsEl,
  h("details", {}, h("summary", {}, "Corpus sentences"), h("div", { class: "row" }, campaignSelect, corpusFilter), corpusList),
);

function selectedEngines() { return state.engines.filter((e) => state.selected.has(e.name)); }
function engineMeta(name) { return state.engines.find((e) => e.name === name) ?? null; }

function showError(err) {
  if (err instanceof BackendUnreachable) renderBanner(banner, { text: `${err.message.replace(/ Start it with:.*/, "")} Start it with: `, command: err.startCommand });
  else if (err instanceof BackendError) renderBanner(banner, { text: err.message });
  else renderBanner(banner, { text: String(err?.message ?? err) });
}

function update() {
  const sel = selectedEngines();
  const lim = limitModel(sel, textArea.value.length);
  counter.textContent = lim.limit === null ? `${textArea.value.length} characters` : `${lim.counter} characters (limit set by ${lim.limitedBy})`;
  counter.classList.toggle("over", lim.over);
  playBtn.disabled = state.running || lim.playDisabled || sel.length === 0 || textArea.value.trim() === "";
  stopBtn.disabled = !state.running;
  renderEngines(enginesEl, {
    models: state.engines.map(engineOptionModel), selected: state.selected,
    onToggle: (name, on) => {
      if (on) { const e = engineMeta(name); state.selected.set(name, e.voices[0]?.name ?? ""); } else state.selected.delete(name);
      update();
    },
    onVoice: (name, voice) => state.selected.set(name, voice),
  });
  renderSession();
}

function renderSession() {
  const s = state.session;
  if (!s) { panelsEl.replaceChildren(); return; }
  renderPanels(panelsEl, {
    models: s.panels.map((p, index) => ({ model: panelModel(p, engineMeta(p.engine)), index })),
    onReplay: (i) => s.replay(s.panels[i]),
    onRetry: () => play(),
    onEnableAudio: async () => { await state.ctx?.resume(); renderSession(); },
  });
}

async function load(refresh = false) {
  renderBanner(banner, null);
  try {
    const body = await (refresh ? refreshEngines(state.baseUrl) : getEngines(state.baseUrl));
    state.engines = body.engines;
    for (const name of [...state.selected.keys()]) if (!engineMeta(name) || engineMeta(name).availability?.status !== "available") state.selected.delete(name);
  } catch (err) {
    state.engines = [];
    showError(err);
  }
  update();
  try {
    const c = await getCorpus(state.baseUrl);
    state.corpus = c.sentences;
    campaignSelect.replaceChildren(h("option", { value: "" }, "All campaigns"), ...campaigns(state.corpus).map((x) => h("option", { value: x }, x)));
    renderCorpusList();
  } catch { state.corpus = []; renderCorpusList(); }
}

function renderCorpusList() {
  renderCorpus(corpusList, {
    entries: filterCorpus(state.corpus, { campaign: campaignSelect.value, query: corpusFilter.value }),
    onPick: (s) => { textArea.value = activate(s); update(); },
  });
}

function play() {
  if (state.running) return;
  // The audio context is created inside the click handler so the browser allows sound (R12).
  state.ctx = state.ctx ?? new AudioContext();
  state.ctx.resume?.().catch(() => {});
  state.ctx.onstatechange = () => renderSession();
  const selections = [...state.selected.entries()].map(([engine, voice]) => ({ engine, voice }));
  const session = new ComparisonSession({
    text: textArea.value, selections,
    deps: { baseUrl: state.baseUrl, createPlayer: () => createPlayer(AudioContext, state.ctx), notify: () => renderSession() },
  });
  state.session = session;
  state.running = true;
  update();
  session.run().finally(() => { state.running = false; update(); });
}

function stop() { state.session?.stop(); }

update();
load();
