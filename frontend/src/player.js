// Web Audio playback of streamed PCM (R3). Buffers are scheduled back to back at the engine's own sample rate.

const LEAD_S = 0.02;
const UNDERRUN_LEAD_S = 0.005;

export function createPlayer(AudioContextImpl = globalThis.AudioContext, existingContext = null) {
  const ctx = existingContext ?? new AudioContextImpl();
  let sampleRate = 24000;
  let nextTime = null;
  let finished = false;
  let stopped = false;
  let ended = false;
  const sources = new Set();

  const player = {
    onEnded: null,
    underruns: 0,
    context: ctx,
    get state() { return ctx.state === "running" ? "running" : "suspended"; },
    start(rate) {
      sampleRate = rate;
      nextTime = null; finished = false; stopped = false; ended = false;
      player.underruns = 0;
      sources.clear();
    },
    push(float32) {
      if (stopped || float32.length === 0) return;
      const buffer = ctx.createBuffer(1, float32.length, sampleRate);
      buffer.copyToChannel(float32, 0);
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);
      const now = ctx.currentTime;
      if (nextTime === null) nextTime = now + LEAD_S;
      else if (nextTime < now) { player.underruns += 1; nextTime = now + UNDERRUN_LEAD_S; }
      source.start(nextTime);
      nextTime += buffer.duration;
      sources.add(source);
      source.onended = () => { sources.delete(source); check(); };
    },
    finish() { finished = true; check(); },
    stop() {
      stopped = true; ended = true;
      for (const s of sources) { s.onended = null; try { s.stop(); } catch { /* not started */ } }
      sources.clear();
    },
    async resume() { if (ctx.state !== "running") await ctx.resume(); },
  };

  function check() {
    if (finished && !stopped && !ended && sources.size === 0) {
      ended = true;
      player.onEnded?.();
    }
  }
  return player;
}
