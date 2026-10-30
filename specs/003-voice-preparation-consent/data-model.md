# Data Model: Voice Preparation and Consent

All files live under the library root (default `cloned_voices/`, git-ignored). JSON, UTF-8.

## ConsentRecord — `consent/<alias>.json` (FR-001, FR-002)
| Field | Type | Rules |
|-------|------|-------|
| alias | str | pseudonym, `[a-z0-9_-]+`, unique; no real name |
| date | str | `YYYY` or `YYYY-MM-DD`: when the permission was given (year-only allowed when the exact date is unknown) |
| permitted_uses | list[str] | non-empty; from `internal_benchmarking`, `published_results`, `published_demo_audio`, `human_evaluation` |
| allowed_content | list[str] | non-empty; from `outbound_sales`, `collections`, `inbound`, `cloning_prompts` |
| notes | str | optional, free text, no personal identifiers |

Id used by other entities: `consent_id` = `alias`.

## ReferenceRecording — entry in `library.json` → `recordings`
| Field | Type | Notes |
|-------|------|-------|
| recording_id | str | `rec-` + first 12 hex of sha256 of the WAV bytes |
| consent_id | str | required, must exist |
| file | str | `recordings/<recording_id>.wav` (library-owned copy) |
| sample_rate / duration_s | int / float | |
| speech_seconds | float | see research: 30 ms frames |
| snr_estimate_db | float | heuristic |
| accent | str | declared, e.g. `es-CO` |
| warnings | list[str] | `too_short`, `noisy`, `music_not_ruled_out`, `accent_mismatch:<engine>` |
| added | str | ISO date |

## PreparedVoice — entry in `library.json` → `voices`
| Field | Type | Notes |
|-------|------|-------|
| name | str | unique library name matching `[A-Za-z0-9_-]+`, e.g. `valentina-pocket`; Piper voices use their real voice id (`es_MX-claude-high`) because the adapter derives accent and licence from it |
| engine | str | adapter registry name; the only engine that may use it (FR-013) |
| kind | enum | `reference_audio`, `stored_voice_file`, `fixed_voice` (core `VoiceKind`) |
| cloned | bool | false for fixed voices |
| file | str | path relative to root (`voices/<name>/…`), or the existing model path for referenced fixed voices |
| owned | bool | true if the library copied the file (so `remove` deletes it) |
| sha256 | str | of `file` at registration (FR-014) |
| recording_id | str or null | required when `cloned` |
| consent_id | str or null | required when `cloned` (FR-001, SC-001) |
| segment | object or null | `{start_s, length_s}` used for this engine (FR-005); null for fixed voices |
| creation | str | `automated` or `external:<free-text tool/step>` (FR-004) |
| accent_label | str | accent actually produced, as in the engine descriptor |
| warnings | list[str] | copied from the recording at preparation time |
| created | str | ISO date |

Validation: `cloned` ⇒ `recording_id`, `consent_id`, `segment` all present and the consent record exists and is not withdrawn. Name uniqueness: a second registration with an existing or withdrawn name is refused.

## Tombstone — `library.json` → `withdrawn`
`{name, recording_id, date}`: one per removed-by-withdrawal voice. Contains no voice material.

## Layout
```text
cloned_voices/
├── library.json            # {"version": 1, "recordings": {...}, "voices": {...}, "withdrawn": [...]}
├── consent/<alias>.json
├── recordings/<recording_id>.wav
├── voices/<name>/...       # prepared files, library-owned
└── generated/<name>/...    # audio produced with the voice (deleted on remove)
```

## State transitions
`recording added` → `voice prepared/registered` → (`removed` | `withdrawn`). `withdrawn` leaves only a tombstone; results that referenced the voice get `"voice_withdrawn": true`.

## Public view (`public_index()`)
`name, engine, kind, cloned, accent_label, sha256, recording_id`. No paths, no consent contents, no warnings detail beyond codes.
