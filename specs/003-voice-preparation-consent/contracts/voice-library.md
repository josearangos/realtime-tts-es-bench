# Contract: Voice Library

Consumers: adapters' callers (metrics scripts, `smoke`), the backend, the frontend (names only). Requirement ids refer to [spec.md](../spec.md).

## Python API (`tts_bench.voices.LocalVoiceLibrary`)

```python
class LocalVoiceLibrary:
    def __init__(self, root: str | Path = "cloned_voices"): ...

    # consent and recordings
    def add_consent(self, record: ConsentRecord) -> None
    def add_recording(self, wav: Path, consent_id: str, accent: str,
                      no_music_confirmed: bool = False) -> RecordingInfo      # FR-006

    # preparing and registering
    def prepare_segment(self, recording_id: str, engine: str,
                        start_s: float | None = None, length_s: float | None = None) -> Path  # FR-005
    def register(self, name: str, engine: str, kind: VoiceKind, file: Path, *,
                 recording_id: str | None, segment: Segment | None,
                 creation: str, accent_label: str) -> None                    # FR-008, FR-011
    def register_fixed(self, name: str, engine: str, voice_id_or_file: str,
                       accent_label: str, creation: str) -> None              # FR-010

    # resolving
    def resolve(self, name: str, kind: VoiceKind | None = None, *,
                engine: str | None = None, use: str | None = None,
                content: str | None = None) -> VoiceReference               # FR-012..014, FR-016
    def public_index(self) -> list[dict]
    def same_source(self, names: list[str]) -> bool                           # SC-002: false if any voice has no recording_id (fixed voices)

    # removing
    def remove(self, name: str) -> None                                       # FR-009
    def withdraw(self, consent_id: str, results_dir: Path | None = None) -> WithdrawReport
```

`resolve` returns the existing `core.voices.VoiceReference(name, kind, path_or_id)`; `path_or_id` is an absolute path (or the voice id for fixed voices without a file). Order of checks, first failure wins:

| # | Check | Error |
|---|-------|-------|
| 1 | name registered (and not withdrawn) | `VoiceNotFoundError` (lists known names for the engine) |
| 2 | `engine` given ⇒ equals entry engine; `kind` given ⇒ equals entry kind | `VoiceEngineMismatchError` (names both engines) |
| 3 | cloned ⇒ consent record exists | `ConsentRequiredError` |
| 4 | `use` / `content` given ⇒ allowed by consent | `ConsentNotPermittedError` (names the missing permission, or the invalid value if `use` / `content` is outside the allowed vocabulary) |
| 5 | file exists, sha256 equals stored value | `VoiceIntegrityError` ("missing" or "modified", with expected and actual checksum) |

Callers MUST resolve outside timed regions (hashing cost). Report builders MUST pass `use="published_results"` and skip voices listed as withdrawn.

`prepare_segment` and `register` for a cloned voice raise `ConsentRequiredError` if the recording has no consent record. `register` raises `VoiceAlreadyRegisteredError` for an existing or withdrawn name.

`WithdrawReport`: voices removed, files deleted (count), results files marked, tombstones written.

## CLI (`python -m tts_bench.voices <command>`; `--root` defaults to `cloned_voices`)

| Command | Purpose | Exit codes |
|---------|---------|------------|
| `consent add --alias A --date D --uses u1,u2 --content c1,c2` | write a consent record | 0 ok, 2 invalid |
| `add-recording FILE.wav --consent A --accent es-CO [--no-music-confirmed]` | copy, analyze, warn; prints `recording_id` and warnings | 0 ok, 1 refused (no consent) |
| `prepare REC --engine pocket_tts --name N [--start S --length L]` | pocket_tts: write the segment and register it. phonon: write the segment and print the external steps; nothing is registered | 0, 1 |
| `register NAME --engine E --kind K --file F --recording REC [--start S --length L] --creation "text" --accent es-CO` | register an externally created file (e.g. Phonon `.safetensors`) | 0, 1 |
| `assign-fixed NAME --engine piper --voice es_MX-claude-high --accent es-MX` | register a non-cloned fixed voice; for `piper`, NAME MUST equal `--voice` because the Piper adapter derives accent, model id and licence from the voice name | 0, 2 |
| `list [--json]` | public view of registered voices | 0 |
| `show NAME` | full metadata for one voice (local use only) | 0, 1 |
| `verify [NAME]` | check existence and checksum of one or all voices | 0 all ok, 1 any missing/modified |
| `remove NAME` | delete one voice and its generated audio | 0, 1 |
| `withdraw ALIAS [--results-dir results]` | one-action consent withdrawal (SC-004) | 0 |
| `check-repo` | fail if voice material is tracked or ever was in history (SC-003) | 0 clean, 1 found |

Refusals print a one-line reason and, where possible, the corrective command (for example "consent required: run `consent add --alias …`").

## Result-file convention (needed for withdrawal)

Any result JSON that used a library voice carries a top-level `voice` object with at least `name` and `recording_id` (cloned) or `name` (fixed). Generated audio goes under `<root>/generated/<voice name>/`. `withdraw` marks matching result files with `"voice_withdrawn": true`.

## Requirement mapping

| FR | Where |
|----|-------|
| 001, 002 | `consent add`, `add_consent`; checks 3 and registration guard |
| 003, SC-002 | one `recording_id` for all cloning engines; `same_source` (true only for voices from one recording; Phonon `valentina` + Pocket `valentina`) |
| 004 | `creation` field, `docs/voice-preparation.md`, `prepare` output for Phonon |
| 005 | `segment` stored per voice |
| 006 | `add-recording` warnings |
| 007, 015 | `.gitignore`, `check-repo`, `public_index` |
| 008 | PreparedVoice fields |
| 009, SC-004 | `remove`, `withdraw` |
| 010 | `assign-fixed` / `register_fixed`, `cloned=false`, not penalized (no consent or segment required) |
| 011..014 | `register`, `resolve` checks 1, 2, 5 |
| 016 | `resolve` check 4 |
| SC-001 | registration guard + `verify` reports any cloned voice without consent |
| SC-005 | no path outside the library; test greps `src/` for `cloned_voices` literals outside `voices/` and `smoke` defaults |
