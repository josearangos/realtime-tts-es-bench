# Corpus changelog

Versioning rule (research R2): adding sentences is MINOR; editing or removing sentence text is MAJOR; fixing tags, readings (`spoken`), or other metadata is PATCH.

Every result file written by other features must record `corpus_version` and `corpus_hash` (`corpus_stamp(load_corpus())` returns both).

## 1.0.0 - 2026-10-29

- First release. All 123 main and 21 cloning sentences reviewed by the project's native Colombian Spanish reviewer (naturalness, collections tone, spoken readings, regionalisms); every sentence has `reviewed: true`.
- Text unchanged from 0.1.0; only the `reviewed` flag was set.

## 0.1.0 - 2026-10-29

- First draft: 123 fictitious agent-side sentences in Colombian Spanish (outbound sales, collections, inbound) in `sentences.jsonl`, and a held-out cloning subset in `cloning.jsonl`.
- Not yet reviewed by a native Colombian speaker: every sentence has `reviewed: false`. The corpus stays at `0.x` until that review is done.
