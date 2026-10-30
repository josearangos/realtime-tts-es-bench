# Research: Spanish Call Center Test Corpus

## R1. Storage format
- **Decision**: JSON Lines, one sentence per line, sorted by id, with fixed key order.
- **Rationale**: plain text, one line changed per edit gives clean diffs, standard library parses it, and accented characters stay readable (no ASCII escaping).
- **Alternatives**: CSV (awkward with commas, quotes, and list fields); YAML (needs a third-party parser, and implicit typing is risky); one large JSON file (noisy diffs).

## R2. Versioning
- **Decision**: `VERSION.json` holds a semantic-style id (`MAJOR.MINOR.PATCH`), the date, counts, and a SHA-256 hash of the sentence files; `CHANGELOG.md` documents each release. Adding sentences is MINOR, editing or removing text is MAJOR, fixing tags or readings is PATCH. The validator fails when the hash does not match the version file, forcing a version bump with any content change.
- **Rationale**: satisfies "version changes when the corpus changes and the change is documented" automatically.
- **Alternatives**: git commit hash only (not stable across copies of the result files); date-based ids (carry no change meaning).

## R3. Cloning subset
- **Decision**: separate file `cloning.jsonl` with the same schema, `subset` field set to `cloning`. Overlap check compares normalized text (lowercase, accents kept, punctuation and extra spaces removed) against supplied transcript files, both exact match and a high word-overlap threshold (Jaccard of word sets at or above 0.8) to catch near copies. The main corpus is also checked against the cloning subset so the two stay disjoint.
- **Rationale**: a physically separate file makes "held-out" obvious and keeps the main run order unchanged.
- **Alternatives**: a subset flag inside one file (easy to mix by accident).

## R4. Reference transcripts
- **Decision**: the validator takes transcript paths as arguments (plain text, one sentence or paragraph per file, split on sentence punctuation); by default it looks in `cloned_voices/*/transcript.txt` when present. When none exist it reports the overlap check as "not run", never as passed.
- **Rationale**: transcripts belong to the cloning feature and its git-ignored voice folders; honest reporting forbids a silent pass.
- **Alternatives**: copying transcripts into the corpus (would leak consented-voice material).

## R5. Normalized spoken reading
- **Decision**: every sentence containing a digit, currency symbol, percent sign, or acronym carries a `spoken` field, written in full Spanish words, using Colombian conventions: pesos amounts read as "cuarenta y cinco mil novecientos pesos", phone numbers digit groups, dates and times in words, acronyms either spelled (PQR as "pe cu erre") or read as words (SMS as "ese eme ese"). The validator checks the field exists and contains no digits or symbols; it cannot check correctness, so reviewers confirm during corpus review.
- **Alternatives**: an automatic number-to-words library (adds a dependency and hides ambiguity decisions).

## R6. Feature tag detection
- **Decision**: tags are authored by hand and checked, not inferred; the validator also cross-checks the objective ones: `long` requires 25 or more words, `short` requires 5 or fewer, `question` requires a question mark, `amount_cop` and `number` require digits in the text, `acronym` requires an uppercase run of two or more letters or a digit-plus-letter form such as 4G.
- **Rationale**: catches mislabeling while keeping judgment tags (difficult words, names) manual.

## R7. Scenario coverage lists
- **Decision**: a fixed scenario vocabulary per campaign type, matching spec FR-003 to FR-005, with at least 2 sentences per scenario; cross-cutting scenarios `disclosure` and `short_response` need at least 5 each.
- **Rationale**: turns the "covers" statements of the spec into countable checks.

## R8. Regionalisms and address forms
- **Decision**: `REGIONALISMS.md` lists each expression (for example "con gusto", "a la orden", "regálame un momento", "vale", "listo", "celular", "plata", "tarjeta de crédito", "cuota", "paz y salvo"), its region, register, and the sentence ids using it. `address` field takes `usted`, `tu`, or `vos`; usted is the default.
- **Note**: regional claims come from the authors' judgment and must be reviewed by a native Colombian speaker before the first release.

## R9. Safety of content
- **Decision**: fictitious company names, names, and numbers use reserved or obviously invalid patterns (phone numbers beginning with a reserved test prefix such as 300 000 xxxx; account numbers of the form XXXX with fake digits). Collections content is checked against a small banned-phrase list (threats, legal intimidation, public shaming terms); the list is a safety net, and manual review remains the main control.
- **Alternatives**: no automated check (rejected: cheap to add).

## R10. Realism and discriminating power
- **Decision**: authoring rules are agent-side, spoken register, written as continuous call scripts per scenario (opening, offer, objection, close) so sentences keep realistic order and phrasing; the `probes` field records the difficulty each sentence targets, and the validator requires at least 5 sentences per `probes` value. A `reviewed` flag is set only after native Colombian speaker approval, and the release check fails if any sentence is unreviewed.
- **Rationale**: a corpus that only counts tags can still be bland; the goal is text that separates good voice agents from bad ones on real call center difficulty.
- **Limit**: realism is human judgment; the validator can enforce that review happened, not that it was right.

## R11. Version stamping while authoring
- **Decision**: `python -m tts_bench.corpus stamp` recomputes counts and hash in `VERSION.json`. While the version is `0.x`, a hash mismatch is a warning; from `1.0.0` it is an error. A content change on a released version still requires a version bump and changelog entry.
- **Rationale**: authoring changes the files constantly; forcing a stamp each time would block progress checks.
