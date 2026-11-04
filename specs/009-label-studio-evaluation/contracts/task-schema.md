# Contract: Task Data (annotator-visible)

Only these keys may appear in `task.data`; a unit test fails on any other key or on any value that contains an engine name, voice name, sentence id or a filename not matching `^[0-9a-f]{12}\.wav$`.

| Project | Keys |
|---|---|
| mos | `item_id`, `audio`, `text` |
| cmos | `item_id`, `audio_a`, `audio_b`, `text` |
| sim | `item_id`, `reference`, `audio`, `text` |

- `audio*`/`reference`: `/data/local-files/?d=<12hex>.wav`.
- `text`: the sentence's spoken form shown for pronunciation judgement (Spanish).
- Attention-instructed tasks carry the instruction inside `text` (e.g. "Control de atención: seleccione «Mala» en todas las preguntas.").
- Private fields live only in the mapping ([data-model.md](../data-model.md)).
- Repeats and degraded anchors are indistinguishable from test tasks.
