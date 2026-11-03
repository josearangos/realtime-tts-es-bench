# Real-time performance comparison: Piper, Phonon and Pocket TTS

Generated from the six results files in this directory with `python -m tts_bench.metrics compare results/perf/*.json`, then annotated by hand (sections 1, 2 and 4 to 6 are written by hand; the tables in section 3 are the tool's output).

## 1. What the experiment was

Three Spanish text-to-speech engines were each run once in **cold** mode and once in **warm** mode over the same corpus, on the same machine, one engine per process (each in its own virtual environment).

- **Corpus:** the main Spanish call center corpus, version `1.0.0` (hash `e4fb3b0a…6cf4f36a4`), 123 sentences, always processed in corpus order.
- **Repetitions:** 5 passes over the whole corpus per run, so a warm run has 615 measured requests and a cold run 614 (the first request is reported apart, see below).
- **Machine:** Apple M2 Pro, 10 cores, 16 GiB RAM, macOS (Darwin 25.2.0), Python 3.11.13.
- **Engines and voices:**

| Engine | Version | Voice used | Notes |
|---|---|---|---|
| piper | 1.8.0 | `es_MX-claude-high` | fixed catalog voice, Mexican Spanish. It is the closest available to Colombian Spanish and is **not** Colombian |
| phonon | 0.5.0 | `valentina-phonon` | cloned voice (es-CO) stored as a voice file |
| pocket_tts | 4.0.1 | `valentina-pocket` | cloned voice (es-CO) from reference audio |

- **What is measured:** for each sentence, the time the engine takes to start and finish producing audio, and the length of audio produced. Audio is discarded: nothing is saved or played back, so no audio quality is evaluated here.
- **Raw data:** every sentence of every repetition is stored in the JSON files (`*-cold-*.json`, `*-warm-*.json`), together with the full environment record (hardware, library versions, exact command, corpus hash).

## 2. Definitions

The authoritative definitions, with the exact start and end instants, are in [`docs/metrics.md`](../../docs/metrics.md) and in `specs/004-realtime-performance-metrics/contracts/results-file.md`. A summary:

**Modes**

- **Cold:** the model is loaded in a fresh process, and the very first request is measured separately (the *first request*). It captures one-time costs such as lazy initialisation. That first request is excluded from the steady-state figures, and its extra cost over the median is reported as the *first-request penalty*.
- **Warm:** after loading, a few requests (3 here) are run and thrown away so that start-up effects are gone. Every request after that is measured.

**Metrics** (all times use a monotonic clock, `time.perf_counter_ns()`)

| Metric | Meaning | Unit |
|---|---|---|
| Load time | time for the engine to load, from just before `load()` until it returns | ms |
| Generation time | from just before the synthesis call until the last audio is delivered | ms |
| TTFA (time to first audio) | from just before the call until the first non-empty audio chunk is delivered | ms |
| RTF (real-time factor) | generation time divided by the duration of the audio produced. Below 1 means faster than real time; lower is better | ratio |
| Throughput | audio seconds produced per wall-clock second over a repetition, from its first request start to its last request finish; the run value is the median over repetitions. It is roughly the inverse of RTF | audio s per s |
| Chunk latency | for streaming engines, when each chunk arrived and the gap since the previous chunk (kept in the raw data) | ms |
| p50 / p95 | median and 95th percentile (linear interpolation) over all valid sentence x repetition values | n/a |
| Peak RAM | process lifetime peak resident memory, in MiB | MiB |
| CPU | process CPU time over wall time during the measured phase, as a percentage of one core, so it can exceed 100 | % |
| VRAM | peak GPU memory, or "not available" when it cannot be measured (this Mac has no NVIDIA GPU; unified memory counts under RAM) | MiB |
| reliable | false when more than 10 % of the requests failed or returned empty audio | yes/no |
| n | number of valid measurements behind the percentiles | count |

**Streaming granularity.** TTFA only means something for engines that stream. `chunk` engines (phonon, pocket_tts) deliver audio in pieces, so TTFA is the delay to the first piece. Piper is `sentence`: it delivers the whole sentence at once, so its TTFA is simply the full sentence latency and **must not be compared directly** with the TTFA of a chunk engine.

"not available" always means "could not be measured", never an estimate.

## 3. Results

> Note: environments also differ in software.libraries, config.thread_settings (different virtual environments per engine). Hardware, corpus, subset and locality are identical, so the comparison was accepted.

### cold

| engine | voice | granularity | load time | TTFA p50/p95 | RTF p50/p95 | throughput (audio s/s) | peak RAM | CPU | VRAM | reliable | n |
|---|---|---|---|---|---|---|---|---|---|---|---|
| phonon | valentina-phonon | chunk | 226 ms | 8.2 / 19.2 ms | 0.058 / 0.114 | 14.75 | 301 MiB | 21% | not available | yes | 614 |
| piper | es_MX-claude-high | sentence | 63 ms | 162.5 / 312.8 ms | 0.029 / 0.033 | 34.38 | 734 MiB | 493% | not available | yes | 614 |
| pocket_tts | valentina-pocket | chunk | 6679 ms | 77.2 / 89.2 ms | 0.244 / 0.297 | 3.98 | 1660 MiB | 163% | not available | yes | 614 |

### warm

| engine | voice | granularity | load time | TTFA p50/p95 | RTF p50/p95 | throughput (audio s/s) | peak RAM | CPU | VRAM | reliable | n |
|---|---|---|---|---|---|---|---|---|---|---|---|
| phonon | valentina-phonon | chunk | 115 ms | 8.0 / 15.7 ms | 0.056 / 0.100 | 16.43 | 301 MiB | 20% | not available | yes | 615 |
| piper | es_MX-claude-high | sentence | 37 ms | 163.5 / 317.4 ms | 0.029 / 0.034 | 33.81 | 769 MiB | 489% | not available | yes | 615 |
| pocket_tts | valentina-pocket | chunk | 3835 ms | 79.6 / 88.1 ms | 0.282 / 0.301 | 3.81 | 1807 MiB | 167% | not available | yes | 615 |

### First request in cold mode (outside the steady-state figures above)

| engine | first-request generation time | first-request TTFA | penalty over the steady-state median |
|---|---|---|---|
| phonon | 836 ms | 35 ms | +470 ms |
| piper | 1263 ms | 1078 ms | +1097 ms |
| pocket_tts | 3446 ms | 1808 ms | +1980 ms |

## 4. Conclusions

1. **All three engines are faster than real time** on this machine (RTF well below 1), so none is limited by raw synthesis speed for a single stream.
2. **Fastest overall: Piper** (RTF 0.029, about 34 s of audio per second). But it only delivers audio once per sentence, so a caller hears nothing until the whole sentence is ready: about 163 ms typically and 313-317 ms at p95. That is its TTFA.
3. **Best time to first audio: Phonon**, around 8 ms (p95 16-19 ms), with an RTF of 0.056-0.058. For a live call, where the first sound matters most, this is the standout result, and it also uses the least memory (301 MiB).
4. **Pocket TTS is the slowest and heaviest**: RTF 0.24-0.28, about 4 audio seconds per second, 1.7-1.8 GiB of RAM and the longest load (3.8-6.7 s). Its TTFA (about 77-80 ms) is still reasonable and very stable (p95 within 12 ms of p50).
5. **Cold start matters.** Both Pocket TTS (about +2.0 s) and Piper (about +1.1 s) pay a large one-time penalty on the first request, much larger than their steady-state latency; Phonon pays about +0.5 s. A real deployment should warm the engine before taking calls.
6. **Cold and warm steady-state figures are almost identical** for Piper and Phonon. The cold one-time cost is concentrated in the first request and in loading, which is why it is reported separately.
7. **Piper uses many cores** (about 490 % of one core) while Phonon uses about 20 % and Pocket TTS about 165 %. If several calls share one machine, Piper's throughput will not simply multiply. This was not tested here (one stream at a time).

## 5. Recommendation: real-time Spanish TTS with a cloned voice

**Phonon is the best of the three on the measured criteria.**

- **Piper is out for this use case.** It was run with a fixed catalog voice (`es_MX-claude-high`, `fixed_voice`) and the benchmark does not use it for voice cloning. Its speed is the best here, but it cannot produce the cloned voice, so it is useful only as a speed reference or for a non-cloned deployment.
- **Between the two cloning engines, Phonon wins on every latency and cost figure:**

| Criterion | Phonon | Pocket TTS |
|---|---|---|
| Time to first audio (p50 / p95, warm) | 8.0 / 15.7 ms | 79.6 / 88.1 ms |
| RTF p50 (warm) | 0.056 | 0.282 |
| Throughput (warm) | 16.4 audio s/s | 3.8 audio s/s |
| Peak RAM | 301 MiB | 1807 MiB |
| Load time (warm / cold) | 115 / 226 ms | 3835 / 6679 ms |
| First-request penalty (cold) | +470 ms | +1980 ms |

  It starts talking about 10 times sooner, generates about 4 times faster per audio second, uses about a sixth of the memory, and loads and warms up much faster.

**What this recommendation does not cover.** This benchmark measures speed and resource use only. It says nothing about how well each engine reproduces the target voice, how natural or intelligible the Spanish is, or whether the Colombian accent is kept. Those need the quality evaluation (listening tests and objective checks) before a final choice. If Phonon's voice similarity or naturalness turns out clearly worse, Pocket TTS is still fast enough for real time (RTF 0.28, TTFA under 100 ms) and could be preferred on quality grounds. The results come from single runs with the caveats below, so the gap between the two is large enough to trust in direction, but the exact figures should be rechecked on an idle, plugged-in machine before publishing.

## 6. Caveats: read before quoting these numbers

- **Background load warnings.** `background_load.warning` is true in four of the six runs (phonon cold, piper cold, piper warm, pocket_tts cold): the 1-minute load average per core was above the 0.25 threshold before or after the run. The check is indicative (the average lags), but those runs were not on a fully idle machine.
- **Power state.** The Pocket TTS runs were made on battery with macOS Low Power Mode on, which can slow the CPU. Power state is not stored in the results files, so it is unknown for the other four runs. This may be why Pocket TTS warm (RTF 0.282) came out slower than cold (0.244), the opposite of what is expected; treat that difference as noise, not as an effect.
- **No reproducibility check on real hardware.** Each engine and mode was run once, so the 10 % repeatability criterion (SC-002) has only been verified with the fake engine.
- **Single stream, local, no audio quality.** One request at a time, no network, and nothing here says how good the voices sound or how natural they are. Piper's voice is Mexican Spanish, not Colombian.
- **Different voices.** Piper uses a catalog voice and the other two use cloned voices. The engine, not the voice, is what is being timed, but the voices differ.
- **Re-running `compare` will overwrite this file.** The prose sections would be lost; copy them elsewhere first or write the tables to another path with `--out`.
