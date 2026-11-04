# Human evaluation protocol

Complements the deterministic metrics (intelligibility, speaker similarity, latency) with listener judgements of **naturalidad, pronunciación, prosodia**, A/B preference (**CMOS**) and cloned-voice **similarity (SIM)**. Human scores are reported separately from the automatic metrics (Constitution IV). Operations are in [evaluation/README.md](../evaluation/README.md).

## Step-by-step run

Run everything from the repository root. Docker Desktop (or Engine with Compose v2) must be running.

**1. Have synthesized audio.** The evaluation reads the clips from the earlier features (`output/intelligibility/*`, `output/speaker/*`, each with a `manifest.json`). Synthesize them first if needed (see `docs/intelligibility.md` and `docs/speaker-similarity.md`). Clips from anywhere else can be listed in a JSONL file (`engine, voice, accent, cloned, sentence_id, wav[, reference]`) and passed with `--source-manifest`.

**2. Choose the batch.** Edit `evaluation/batch.toml`: `seed`, `sentences_per_condition`, `repeat_rate`, `attention_rate`, and optionally `conditions` to restrict engines/voices. The batch freezes at the first `make eval-up`; later edits are refused until `make eval-new-batch`.

**3. Create the environment file.**
```bash
cp evaluation/.env.example evaluation/.env
```
Change `LS_ADMIN_PASSWORD` and `LS_API_TOKEN`. Keep `LS_BIND=127.0.0.1` unless annotators must connect over your network (then use real secrets and a trusted network, see `evaluation/README.md`).

**4. Start and provision.**
```bash
make eval-up
```
The first run builds two images and needs the network (several minutes). It starts Label Studio, then prepares the batch (normalized, opaque-named audio in `output/evaluation/served/`, private mapping in `output/evaluation/private/`) and creates the three projects with their tasks. Running it again is safe and creates nothing new.

**5. Check as admin.** Open http://127.0.0.1:8080 and log in with `LS_ADMIN_USER` / `LS_ADMIN_PASSWORD`. You should see **MOS**, **CMOS** and **SIM**. Open one task and press play on the audio. `make eval-inspect` prints exactly what annotators will see: there must be no engine or voice names.

**6. Create the annotators** (one per person, pseudonymous):
```bash
make eval-annotator ID=a01
make eval-annotator ID=a02
```
Each command prints a login (`a01@eval.invalid`) and a password **once**: hand it to that person privately. `make eval-annotator ID=a01 RESET=1` issues a new password.

**7. Brief the annotators.** Native Spanish speakers, headphones, quiet room, listen to each audio at least once completely, judge the voice and ignore the content. Ask each person to complete whole projects (MOS, CMOS and SIM for cloned voices). Tell them not to delete tasks (Community Edition cannot prevent it). They open the URL, log in with their email and password, choose a project and press **Label All Tasks**; the order is random.

**8. Collect.** Annotators work in the browser. Use **Data Manager** as admin to follow progress. Do not change `batch.toml`, the scales or the corpus during collection. Take a backup after each session:
```bash
make eval-backup
```

**9. Export and read the quality report** when everyone has finished:
```bash
make eval-export                 # writes results/human/
make eval-export OUT=/some/dir   # or another directory
```
Open `results/human/quality.json` and check the `flagged` annotators. Filter with `role == "test"` for scores, and decide and document any exclusion (the tool never excludes). The export aborts if any annotation comes from an account that is not `aNN@eval.invalid`, so annotate only with the accounts from step 6.

**10. Stop or finish.**
```bash
make eval-down     # stops containers, keeps all data
make eval-up       # resumes where you left off (works offline once the images exist)
```
To restore a backup into a clean environment: `make eval-reset` (type `RESET`), then `make eval-restore FILE=backups/evaluation/<UTC>.tar.gz` (the restore asks for confirmation when data exists, or use `CONFIRM=RESTORE`).

**11. Optional operations.**
- New round of evaluation: change `seed` in `batch.toml`, then `make eval-new-batch` (the old batch is archived; old annotations stay exportable).
- Consent withdrawn for a voice: `make eval-purge-voice VOICE=<voice name>`, then export again.
- Wipe everything: `make eval-reset` (type `RESET`).

**Common problems**: see the troubleshooting table in `evaluation/README.md` (port in use, Docker not running, `.env` missing, version guard, exit codes).

## Protocol

- **Annotators**: native Spanish speakers. The organizer attests this; the tool does not enforce it. 2 to 5 annotators, each completes whole projects.
- **Setup**: headphones, quiet room, listen to each audio at least once completely. The instructions page in each project says so in Spanish.
- **Scales** (frozen, Spanish anchors in `src/tts_bench/evaluation/scales.py`): MOS 1–5 per criterion, CMOS −3…+3 (B vs A), SIM 1–5. A SHA-256 of the scale text is stored in `batch.json`, in every export row, and in each project's description. Any wording change gives a new hash and blocks provisioning until a new batch is started on purpose.
- **Halo effect**: the three MOS criteria are rated on the same audio in one project, which saves listening but lets one impression color all three. Distinct anchors reduce this; read the three scores with that caveat.
- **Blindness**: tasks carry only an opaque id, opaque audio file names and the sentence text. Task order is random (seeded, plus Label Studio's random sampling) and A/B positions are balanced per pair. Loudness is equalized (RMS −23 dBFS).
- **Same sentences** for every condition inside a comparison group (a corpus subset), stratified by campaign.

## Quality control

About 10 % of items are **repeats** (same audio, new id) and about 5 % **attention checks**: instructed responses over a generated tone ("marque 4 estrellas…") and degraded anchors (a real clip with noise at 0 dB SNR, expected ≤ 2). They look like normal tasks. `quality.json` reports per annotator: repeat pairs, mean absolute difference, share within ±1, failed checks, and a `flagged` verdict with reasons (defaults in `batch.toml`: at least 70 % of repeats within ±1, at most 1 failed check). **Nothing is excluded automatically.** Exclusion is an analysis decision: export rows keep `role` so you can filter QC rows and flagged annotators and say so in the report.

## Reading the export

`make eval-export` writes to `results/human/`:

- `annotations.jsonl` / `.csv`: one row per annotation with batch id, project, `item_id`, pseudonymous `annotator_id` (`a01`), `role` (`test`, `repeat`, `attention_*`), engine/voice/accent/cloned (CMOS: `engine_a/voice_a/engine_b/voice_b`), sentence id, corpus version, scale hash, Label Studio version, ratings, lead time.
- `quality.json`, and `MANIFEST.json` (config hash, seed, counts, loudness, file hashes, Python/numpy/OS/Label Studio versions, command).

Rows are sorted by `(project, item_id, annotator_id)`, so two exports of the same state are byte-identical. No emails, audio or reference recordings are written. Use `role == "test"` for scores.

## Privacy, consent and licensing (Constitution VI)

- Annotator accounts are `aNN@eval.invalid` with no names; the export aborts on any other email form (it names the user id, never the email).
- Audio, the blind mapping, backups and `.env` are git-ignored. Reference recordings appear only inside the local SIM project and never in exports.
- Cloned voices are used under the owner's standing consent. If consent is withdrawn, `make eval-purge-voice VOICE=<name>` deletes that voice's served audio (including SIM references), its tasks and its mapping rows, and logs the purge in `output/evaluation/private/purges.jsonl`. Re-export and re-analyse afterwards.

## Compliance notes

- **IV**: blind, randomized, frozen scales; human results never merged with automatic scores.
- **VI**: pseudonymous ids, purge command, nothing sensitive tracked.
- All annotator-facing text is Spanish (Constitution II); only Label Studio Community Edition is used.
