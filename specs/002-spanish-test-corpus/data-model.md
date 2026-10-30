# Data Model: Spanish Call Center Test Corpus

## Sentence (one JSON line)

| Field | Type | Rules |
|-------|------|-------|
| `id` | string | unique; pattern `<prefix>-NNN` (`VEN` outbound sales, `COB` collections, `ENT` inbound, `CLO` cloning); file sorted by id |
| `text` | string | non-empty Spanish text, exactly what is sent to the engine; no leading or trailing spaces |
| `campaign` | enum | `outbound_sales`, `collections`, `inbound` |
| `scenario` | enum | per-campaign list below, plus `disclosure` and `short_response` |
| `tags` | list of enum | see Feature tags; may be empty only if none apply |
| `address` | enum | `usted` (default), `tu`, `vos`, `none` (no address form present) |
| `spoken` | string or absent | required when `text` has digits, symbols, or acronyms; contains none of them |
| `probes` | enum | the main difficulty tested: `amount`, `phone_or_account`, `datetime`, `acronym`, `name`, `long_disclosure`, `fast_ack`, `regionalism`, `prosody_question`, `hard_word`; required |
| `reviewed` | boolean | true only after native-speaker approval; release requires all true |
| `subset` | enum | `main` or `cloning`; must match the file it is in |

### Scenarios
- **outbound_sales**: `mobile_prepaid`, `mobile_postpaid`, `portability`, `device_promo`, `internet_fiber`, `upgrade`, `pricing`, `objection`
- **collections**: `card_balance`, `overdue_installment`, `due_date`, `payment_agreement`, `payment_channel`, `payment_reminder`
- **inbound**: `greeting`, `identity_verification`, `billing_query`, `complaint`, `tech_support`, `plan_change`, `closing`
- **cross-cutting (any campaign)**: `disclosure`, `short_response`

### Feature tags (minimum 10 sentences each in the main file)
`amount_cop`, `number` (phone or account), `datetime`, `acronym`, `proper_name`, `question`, `long`, `short`, `hard_word`

## Tags and probes
`probes` is the main difficulty of a sentence; `tags` lists every feature present. Where a probe has a matching tag (`amount`→`amount_cop`, `phone_or_account`→`number`, `datetime`→`datetime`, `acronym`→`acronym`, `name`→`proper_name`, `long_disclosure`→`long`, `fast_ack`→`short`, `prosody_question`→`question`, `hard_word`→`hard_word`), the sentence MUST include that tag. `regionalism` has no tag and is checked against `REGIONALISMS.md`.

## Corpus Version (`VERSION.json`)

| Field | Rules |
|-------|-------|
| `version` | `MAJOR.MINOR.PATCH` |
| `date` | ISO date |
| `counts` | per campaign and total, main and cloning |
| `content_sha256` | hash of `sentences.jsonl` and `cloning.jsonl` contents; must match files |

Each version has a matching heading in `CHANGELOG.md`.

## Relationships and rules
- `disclosure` and `short_response` sentences are counted in addition to the minimum of 2 per campaign scenario.
- Main and cloning files have disjoint ids and disjoint normalized texts.
- Cloning subset covers all three campaigns (at least 5 each).
- Near-duplicate threshold: normalized word-set Jaccard of 0.9 or more within the corpus is reported.
- Validation result: list of errors (block use) and warnings (reported); transcript overlap check reports `passed`, `failed`, or `not run`.

## Fixed values
- `short`: 5 words or fewer; `long`: 25 words or more.
- `address`: at least 5 sentences with `tu` and 5 with `vos` in the main file.
- Cloning subset: about 20 sentences, at least 5 per campaign.
- Transcript location: `cloned_voices/<voice>/transcript.txt`.
