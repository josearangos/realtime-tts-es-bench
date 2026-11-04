// Run controller: one EnginePanel per engine, strictly sequential (FR-005).
import { openSynthesis } from "./stream.js";
import { int16ToFloat32 } from "./pcm.js";

export class EnginePanel {
  constructor({ engine, voice }) {
    this.engine = engine;
    this.voice = voice;
    this.reset();
  }
  reset() {
    this.state = "waiting";
    this.start = null;
    this.chunks = [];
    this.summary = null;
    this.error = null;
    this.browser = { sent_at: null, first_chunk_at: null, first_audio_scheduled_at: null, ended_at: null };
    this.underruns = 0;
    this.audio_blocked = false;
  }
  get heardAfterMs() {
    const { sent_at, first_audio_scheduled_at } = this.browser;
    return sent_at !== null && first_audio_scheduled_at !== null ? first_audio_scheduled_at - sent_at : null;
  }
}

const defaultNow = () => globalThis.performance.now();
const requestId = () => `web-${Math.random().toString(36).slice(2, 10)}`;

// Runs one panel. Returns {promise, stop}; the promise resolves when the request AND its playback have ended.
export function runPanel(panel, text, deps) {
  const { baseUrl, createPlayer, open = openSynthesis, WebSocketImpl, now = defaultNow, notify = () => {} } = deps;
  panel.reset();
  let player = null;
  let handle = null;
  let finishedFlag = false;
  let streamClosed = false;
  let playbackEnded = false;
  let stoppedByUser = false;
  let resolve;
  const promise = new Promise((r) => { resolve = r; });

  const set = (state) => { panel.state = state; notify(panel); };
  const complete = () => {
    if (finishedFlag) return;
    finishedFlag = true;
    panel.browser.ended_at = now();
    notify(panel);
    resolve(panel);
  };
  const maybeFinish = () => {
    if (finishedFlag || stoppedByUser) return;
    if (panel.error) { if (!player || playbackEnded || streamClosed) { if (!player || playbackEnded) complete(); } return; }
    if (panel.summary && (!player || playbackEnded)) { set("done"); complete(); }
  };

  set("connecting");
  panel.browser.sent_at = now();

  const handlers = {
    onStart(msg) { panel.start = msg; if (panel.state === "connecting") set("streaming"); },
    onChunk(meta, int16) {
      panel.chunks.push({ meta, pcm: int16 });
      if (!player) {
        player = createPlayer();
        player.onEnded = () => { playbackEnded = true; panel.browser.ended_at = now(); maybeFinish(); };
        player.start(panel.start?.sample_rate ?? 24000);
        panel.browser.first_chunk_at = now();
        player.push(int16ToFloat32(int16));
        panel.browser.first_audio_scheduled_at = now();
        set("playing");
      } else {
        player.push(int16ToFloat32(int16));
      }
      panel.underruns = player.underruns;
      panel.audio_blocked = player.state === "suspended";
      notify(panel);
    },
    onSummary(summary) {
      panel.summary = summary;
      notify(panel);
      if (player) player.finish();
      maybeFinish();
    },
    onError(err) {
      if (stoppedByUser) return;
      panel.error = err;
      set("failed");
      if (player) player.finish(); // let what was received finish playing
      maybeFinish();
    },
    onClose() {
      streamClosed = true;
      maybeFinish();
    },
  };

  handle = open(baseUrl, { engine: panel.engine, voice: panel.voice, text, options: { request_id: requestId() } }, handlers, WebSocketImpl);

  return {
    promise,
    stop() {
      if (finishedFlag) return;
      stoppedByUser = true;
      handle?.cancel();
      player?.stop();
      set("cancelled");
      complete();
    },
  };
}

export class ComparisonSession {
  constructor({ text, selections, deps }) {
    this.text = text;
    this.deps = deps;
    this.panels = selections.map((s) => new EnginePanel(s));
    this.state = "idle";
    this.current = -1;
    this._running = null;
    this._replay = null;
    this._stopped = false;
  }

  async run() {
    this.state = "running";
    const notify = this.deps.notify ?? (() => {});
    for (let i = 0; i < this.panels.length; i++) {
      const panel = this.panels[i];
      if (this._stopped) { panel.state = "not_run"; notify(panel); continue; }
      this.current = i;
      this._running = runPanel(panel, this.text, this.deps);
      await this._running.promise;
      this._running = null;
    }
    this.current = -1;
    this.state = this._stopped ? "stopped" : "finished";
    notify(null);
  }

  stop() {
    this._stopped = true;
    this._replay?.stop();
    const notify = this.deps.notify ?? (() => {});
    this._running?.stop();
    for (const p of this.panels) if (p.state === "waiting") { p.state = "not_run"; notify(p); }
  }

  // Replays stored audio; sends nothing on any socket.
  replay(panel) {
    if (panel.state !== "done" || panel.chunks.length === 0) return Promise.resolve();
    const notify = this.deps.notify ?? (() => {});
    const player = this.deps.createPlayer();
    this._replay = player;
    panel.state = "playing";
    notify(panel);
    return new Promise((resolve) => {
      player.onEnded = () => { panel.state = "done"; this._replay = null; notify(panel); resolve(); };
      player.start(panel.start?.sample_rate ?? 24000);
      for (const c of panel.chunks) player.push(int16ToFloat32(c.pcm));
      panel.audio_blocked = player.state === "suspended";
      player.finish();
    });
  }
}
